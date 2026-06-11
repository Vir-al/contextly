"""
Enhanced Asynchronous Notion Client
Handles fetching all accessible pages, databases, and their content from a Notion workspace
with true async operations, retry logic, and robust data modeling.
"""

import os
import logging
import asyncio
import json
from datetime import datetime
from functools import wraps
from typing import Dict, List, Optional, Any, Literal, Union

from notion_client import AsyncClient
from notion_client.errors import APIResponseError
from pydantic import BaseModel, Field, HttpUrl, field_validator

# --- Configuration ---
# Set up logging to provide visibility into the client's operations.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Pydantic Models for Robust Data Handling ---
# These models ensure that the data fetched from Notion conforms to a known structure.

class NotionParent(BaseModel):
    """Represents the parent of a Notion object (Page or Database)."""
    type: str
    id: str = Field(alias="database_id", default=None) or Field(alias="page_id", default=None) or Field(alias="workspace", default=None)

    @field_validator('id', mode='before')
    @classmethod
    def get_parent_id(cls, v, values):
        """Extract the correct ID based on the parent type."""
        parent_data = values.data
        parent_type = parent_data.get('type')
        return parent_data.get(f"{parent_type}_id")


class NotionBaseModel(BaseModel):
    """A base model for Notion objects, providing common fields."""
    id: str
    url: HttpUrl
    created_time: datetime
    last_edited_time: datetime
    properties: Dict[str, Any]
    parent: NotionParent

    class Config:
        arbitrary_types_allowed = True


class NotionPage(NotionBaseModel):
    """Represents a Notion page with its content and child blocks."""
    title: str
    content_text: Optional[str] = None
    children_blocks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class NotionDatabase(NotionBaseModel):
    """Represents a Notion database with its schema and contained pages."""
    title: str
    pages: List[NotionPage] = Field(default_factory=list)


# --- API Call Decorator for Retries ---

def retry_on_error(retries: int = 3, delay: int = 2, backoff: int = 2):
    """
    A decorator to retry a function call on APIResponseError.
    This is crucial for handling transient network issues or API rate limits.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except APIResponseError as e:
                    if e.status in [500, 502, 503, 504]: # Server-side errors
                        logger.warning(f"API error ({e.code}, status: {e.status}), retrying in {current_delay}s... ({i + 1}/{retries})")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Client-side API error ({e.code}): {e.message}")
                        raise  # Non-retriable error
                except Exception as e:
                    logger.error(f"An unexpected error occurred in {func.__name__}: {e}")
                    raise
            raise APIResponseError(f"Function {func.__name__} failed after {retries} retries.")
        return wrapper
    return decorator

# --- Main Notion Client ---

class NotionClient:
    """
    An enhanced, asynchronous Notion client for fetching workspace data.
    
    Key Features:
    - True asynchronous operations using `notion_client.AsyncClient`.
    - Automatic retry logic for transient API errors.
    - Robust data validation and modeling with Pydantic.
    - Comprehensive fetching of pages, databases, and content.
    - Clear separation of concerns for fetching, parsing, and utility functions.
    """

    def __init__(self, integration_token: Optional[str] = None):
        """
        Initializes the asynchronous Notion client.

        Args:
            integration_token: The Notion integration token. If not provided,
                             it falls back to the `NOTION_INTEGRATION_TOKEN`
                             environment variable.
        """
        token = integration_token or os.getenv("NOTION_INTEGRATION_TOKEN")
        if not token:
            raise ValueError(
                "Notion integration token not found. "
                "Please pass it directly or set the NOTION_INTEGRATION_TOKEN environment variable."
            )
        self.client = AsyncClient(auth=token)

    # --- Private Utility Methods ---

    def _extract_title(self, data: Dict[str, Any], object_type: Literal['page', 'database']) -> str:
        """Extracts the title from a Notion page or database object."""
        if object_type == 'page':
            properties = data.get("properties", {})
            for prop in properties.values():
                if prop.get("type") == "title":
                    title_parts = prop.get("title", [])
                    return "".join(part.get("plain_text", "") for part in title_parts)
        elif object_type == 'database':
            title_parts = data.get("title", [])
            return "".join(part.get("plain_text", "") for part in title_parts)
        return "Untitled"

    def _blocks_to_text(self, blocks: List[Dict[str, Any]], indent: str = "") -> str:
        """
        Recursively converts a list of Notion block objects to a plain text string.
        Handles nested blocks and basic formatting.
        """
        text_parts = []
        for block in blocks:
            block_type = block.get("type", "")
            if not block_type:
                continue
            
            content = block.get(block_type, {})
            rich_text = content.get("rich_text", [])
            plain_text = "".join(text.get("plain_text", "") for text in rich_text)

            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "quote"]:
                text_parts.append(f"{indent}{plain_text}")
            elif block_type == "bulleted_list_item":
                text_parts.append(f"{indent}- {plain_text}")
            elif block_type == "numbered_list_item":
                text_parts.append(f"{indent}1. {plain_text}")

            # Recursively process children blocks
            if block.get("has_children") and "children" in block:
                text_parts.append(self._blocks_to_text(block["children"], indent + "  "))
        
        return "\n".join(text_parts)

    # --- Core Asynchronous Fetching Methods ---

    @retry_on_error()
    async def _paginated_fetch(self, method, **kwargs):
        """A generic helper to handle pagination for any Notion API endpoint."""
        all_results = []
        next_cursor = None
        while True:
            response = await method(**kwargs, start_cursor=next_cursor, page_size=100)
            all_results.extend(response.get("results", []))
            next_cursor = response.get("next_cursor")
            if not response.get("has_more") or not next_cursor:
                break
        return all_results

    @retry_on_error()
    async def get_all_block_children(self, block_id: str) -> List[Dict[str, Any]]:
        """
        Recursively fetches all children blocks for a given block (page, etc.).
        This is necessary because the API only returns direct children.
        """
        direct_children = await self._paginated_fetch(self.client.blocks.children.list, block_id=block_id)
        
        tasks = []
        for child in direct_children:
            if child.get("has_children"):
                tasks.append(self.get_all_block_children(child["id"]))
            else:
                # To keep order correct, create a completed future for blocks without children
                future = asyncio.Future()
                future.set_result([])
                tasks.append(future)

        nested_children_results = await asyncio.gather(*tasks)

        for child, nested_children in zip(direct_children, nested_children_results):
            if nested_children:
                child["children"] = nested_children

        return direct_children

    async def get_page(self, page_id: str, fetch_content: bool = True) -> NotionPage:
        """
        Fetches a single Notion page and optionally its full content.

        Args:
            page_id: The ID of the Notion page.
            fetch_content: If True, fetches all content blocks of the page.

        Returns:
            A Pydantic `NotionPage` object.
        """
        try:
            logger.info(f"📄 Fetching page: {page_id}")
            page_data = await self.client.pages.retrieve(page_id=page_id)
            title = self._extract_title(page_data, 'page')

            children_blocks = []
            content_text = ""
            if fetch_content:
                children_blocks = await self.get_all_block_children(page_id)
                content_text = self._blocks_to_text(children_blocks)
            
            return NotionPage(
                title=title,
                content_text=content_text,
                children_blocks=children_blocks,
                **page_data
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch page {page_id}: {e}")
            raise

    async def get_database(self, db_id: str, fetch_pages: bool = True, fetch_page_content: bool = False) -> NotionDatabase:
        """
        Fetches a single Notion database and optionally its contained pages.

        Args:
            db_id: The ID of the Notion database.
            fetch_pages: If True, fetches all pages within the database.
            fetch_page_content: If True, also fetches the full content of each page.

        Returns:
            A Pydantic `NotionDatabase` object.
        """
        try:
            logger.info(f"🗄️ Fetching database: {db_id}")
            db_data = await self.client.databases.retrieve(database_id=db_id)
            title = self._extract_title(db_data, 'database')
            
            pages = []
            if fetch_pages:
                page_results = await self._paginated_fetch(self.client.databases.query, database_id=db_id)
                
                # Concurrently fetch details for all pages found
                page_tasks = [self.get_page(page['id'], fetch_content=fetch_page_content) for page in page_results]
                page_objects = await asyncio.gather(*page_tasks, return_exceptions=True)
                
                pages = [p for p in page_objects if isinstance(p, NotionPage)]
                for error in page_objects:
                    if isinstance(error, Exception):
                        logger.warning(f"⚠️ Could not fetch a page within database {db_id}: {error}")

            return NotionDatabase(
                title=title,
                pages=pages,
                **db_data
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch database {db_id}: {e}")
            raise
    
    async def get_workspace_content(self) -> Dict[str, List[Union[NotionPage, NotionDatabase]]]:
        """
        Fetches all accessible pages and databases from the workspace.

        Returns:
            A dictionary containing lists of `NotionDatabase` and `NotionPage` objects.
        """
        logger.info("🔍 Searching for all accessible resources in the workspace...")
        search_results = await self._paginated_fetch(self.client.search)

        top_level_pages = []
        databases = []
        for res in search_results:
            obj_type = res.get("object")
            if obj_type == "page":
                top_level_pages.append(res)
            elif obj_type == "database":
                databases.append(res)
        
        logger.info(f"Found {len(top_level_pages)} top-level pages and {len(databases)} databases.")
        
        # Fetch full database objects and all their pages
        db_tasks = [self.get_database(db['id'], fetch_pages=True, fetch_page_content=True) for db in databases]
        full_databases = await asyncio.gather(*db_tasks, return_exceptions=True)
        
        # Fetch full page objects for pages not in any of the fetched databases
        db_page_ids = {p.id for db in full_databases if isinstance(db, NotionDatabase) for p in db.pages}
        page_tasks = [self.get_page(p['id'], fetch_content=True) for p in top_level_pages if p['id'] not in db_page_ids]
        full_pages = await asyncio.gather(*page_tasks, return_exceptions=True)

        return {
            "databases": [db for db in full_databases if isinstance(db, NotionDatabase)],
            "pages": [p for p in full_pages if isinstance(p, NotionPage)]
        }

    async def export_workspace_to_json(self, output_dir: str = "notion_export"):
        """
        Exports the entire accessible workspace content into a structured JSON format.

        Args:
            output_dir: The directory where JSON files will be saved.
        """
        logger.info(f"📤 Starting workspace export to '{output_dir}' directory...")
        os.makedirs(output_dir, exist_ok=True)
        
        workspace_data = await self.get_workspace_content()
        databases = workspace_data.get("databases", [])
        pages = workspace_data.get("pages", [])

        # Export databases and their pages
        for db in databases:
            file_path = os.path.join(output_dir, f"db_{db.title.replace(' ', '_')}_{db.id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(db.model_dump(mode='json'), f, indent=2, ensure_ascii=False)
            logger.info(f"  -> Exported database '{db.title}' to {file_path}")

        # Export standalone pages
        for page in pages:
            file_path = os.path.join(output_dir, f"page_{page.title.replace(' ', '_')}_{page.id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(page.model_dump(mode='json'), f, indent=2, ensure_ascii=False)
            logger.info(f"  -> Exported page '{page.title}' to {file_path}")
            
        logger.info(f"✅ Workspace export completed successfully.")


# --- Example Usage ---

async def main():
    """Main function to demonstrate the client's capabilities."""
    logger.info("🚀 Starting Notion Client Demonstration...")
    try:
        # NOTE: Ensure NOTION_INTEGRATION_TOKEN is set in your environment.
        # e.g., export NOTION_INTEGRATION_TOKEN="your_token_here"
        client = NotionClient()

        # --- Get a summary of the workspace ---
        workspace = await client.get_workspace_content()
        print("\n" + "="*50)
        print("📊 WORKSPACE SUMMARY")
        print(f"  Found {len(workspace['databases'])} databases.")
        print(f"  Found {len(workspace['pages'])} standalone pages.")
        print("="*50 + "\n")

        if workspace['databases']:
            print("🗄️ DATABASES:")
            for db in workspace['databases']:
                print(f"  - {db.title} (ID: {db.id}) contains {len(db.pages)} pages.")
        
        if workspace['pages']:
            print("\n📄 STANDALONE PAGES:")
            for page in workspace['pages']:
                print(f"  - {page.title} (ID: {page.id})")
        
        # --- Fetch detailed content for one database ---
        if workspace['databases']:
            first_db = workspace['databases'][0]
            print(f"\n🔬 Fetching full details for database: '{first_db.title}'...")
            detailed_db = await client.get_database(first_db.id, fetch_pages=True, fetch_page_content=True)
            
            if detailed_db.pages:
                first_page = detailed_db.pages[0]
                print(f"\n📜 Content of first page ('{first_page.title}') in database '{detailed_db.title}':")
                print("-"*20)
                print(first_page.content_text or "No text content found.")
                print("-"*20)

        # --- Export the entire workspace ---
        await client.export_workspace_to_json()

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"❌ An error occurred during the demonstration: {e}", exc_info=True)


if __name__ == "__main__":
    # To run this script, you must have the NOTION_INTEGRATION_TOKEN environment
    # variable set with your Notion API token.
    asyncio.run(main())

