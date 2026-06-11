"""
Notion Data Loader
Handles loading and processing documents from Notion databases.
"""

import logging
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import NotionDBLoader
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NotionDataLoader:
    """Loads and processes Notion database documents into a vector store."""
    
    def __init__(self):
        """
        Initializes the NotionDataLoader.

        Args:
            config: An instance of the configuration class.
            notion_tool: An instance of the tool used to interact with the vector store.
        """
        
    
    def load_notion_data(self) -> bool:
        """
        Loads data from all configured Notion databases into the vector store.
        
        Returns:
            True if the process is successful, False otherwise.
        """
      
        
        try:
            logger.info("🔄 Starting Notion data loading...")
            
            loader = NotionDBLoader(
                 integration_token=os.getenv('NOTION_TOKEN'),
                 database_id="21114812ea32805ea3bcfcfa23584f1f",
                 request_timeout_sec=30,  # optional, defaults to 10
                )
           
            
            data = loader.load()
            print(data)

            return True
            
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during Notion data loading: {e}", exc_info=True)
            return False
    
# --- Example Usage ---
if __name__ == '__main__':
    logger.info("🚀 Running Notion Data Loader Standalone Example")
    

    # 2. Instantiate the loader
    notion_loader = NotionDataLoader()
    
    # 3. Check pre-load status
    initial_status = notion_loader.load_notion_data()
    logger.info(f"Initial Collection Status: {initial_status}")

# Notion - RAGS LOAD
# NOTION TOOL _ call qury to Rags 