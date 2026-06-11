"""
Confluence Data Loader
Handles loading and processing Confluence documentation.
"""

import logging
from typing import List
from langchain_community.document_loaders import ConfluenceLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core.config import Config
from tools.confluence_tool import ConfluenceTool

logger = logging.getLogger(__name__)

class ConfluenceDataLoader:
    """Loads and processes Confluence documentation into vector store."""
    
    def __init__(self, config: Config, confluence_tool: ConfluenceTool):
        self.config = config
        self.confluence_tool = confluence_tool
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200
        )
    
    def load_confluence_data(self) -> bool:
        """
        Load Confluence data into the vector store.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.config.is_confluence_configured():
            logger.error("Confluence is not properly configured")
            return False
        
        try:
            logger.info("🔄 Starting Confluence data loading...")
            
            # Initialize Confluence loader
            loader = ConfluenceLoader(
                url=self.config.confluence_url,
                username=self.config.confluence_username,
                api_key=self.config.confluence_api_token
            )
            
            # Load documents from all spaces
            all_docs = []
            for space_key in self.config.confluence_space_keys:
                space_docs = self._load_space_documents(loader, space_key)
                all_docs.extend(space_docs)
            
            if not all_docs:
                logger.warning("⚠️  No documents were loaded from Confluence")
                return False
            
            # Process and store documents
            success = self._process_and_store_documents(all_docs)
            
            if success:
                logger.info("✅ Confluence data loading completed successfully")
            else:
                logger.error("❌ Failed to process and store documents")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error during Confluence data loading: {e}", exc_info=True)
            return False
    
    def _load_space_documents(self, loader: ConfluenceLoader, space_key: str) -> List[Document]:
        """
        Load documents from a specific Confluence space.
        
        Args:
            loader: Confluence loader instance
            space_key: Space key to load from
            
        Returns:
            List of loaded documents
        """
        try:
            logger.info(f"📚 Loading documents from space: {space_key}")
            
            docs = loader.load(
                space_key=space_key,
                include_attachments=False,
                limit=100
            )
            
            # Enrich metadata
            for doc in docs:
                doc.metadata['source_url'] = doc.metadata.get('source', 'Unknown URL')
                doc.metadata['source'] = 'confluence'
                doc.metadata['space'] = space_key
            
            logger.info(f"✅ Loaded {len(docs)} documents from space '{space_key}'")
            return docs
            
        except Exception as e:
            logger.error(f"❌ Failed to load from space '{space_key}': {e}")
            return []
    
    def _process_and_store_documents(self, documents: List[Document]) -> bool:
        """
        Process documents and store them in the vector store.
        
        Args:
            documents: List of documents to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔄 Processing {len(documents)} documents...")
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"📄 Split into {len(chunks)} chunks")
            
            # Store in vector store in batches
            batch_size = 50
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                logger.info(f"💾 Processing batch {batch_num}/{total_batches}")
                self.confluence_tool.add_documents(batch)
            
            logger.info("✅ All documents processed and stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing documents: {e}")
            return False
    
    def check_collection_status(self) -> dict:
        """
        Check the status of the Confluence collection.
        
        Returns:
            Dictionary with collection status information
        """
        try:
            count = self.confluence_tool.get_collection_count()
            return {
                "collection_name": self.config.confluence_collection,
                "document_count": count,
                "status": "active" if count > 0 else "empty",
                "spaces_configured": len(self.config.confluence_space_keys),
                "space_keys": self.config.confluence_space_keys
            }
        except Exception as e:
            return {
                "collection_name": self.config.confluence_collection,
                "document_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def clear_collection(self) -> bool:
        """
        Clear all documents from the Confluence collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would require implementing a clear method in ConfluenceTool
            # For now, we'll log that this operation is not yet implemented
            logger.warning("⚠️  Collection clearing not yet implemented")
            return False
        except Exception as e:
            logger.error(f"❌ Error clearing collection: {e}")
            return False