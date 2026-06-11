"""
Creator Marketing Data Loader
Handles loading and processing creator marketing documentation and data.
"""

import logging
import os
from typing import List, Dict, Any
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader, 
    DirectoryLoader,
    UnstructuredMarkdownLoader,
    PyPDFLoader
)
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.llm_factory import LLMFactory
from core.config import Config

logger = logging.getLogger(__name__)


class CreatorMarketingDataLoader:
    """Loads and processes creator marketing data into vector store."""
    
    def __init__(self, config: Config):
        self.config = config
        llm_factory = LLMFactory(config)
        self.embeddings =  llm_factory.create_embedding_model()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./store/creator_marketing_db")
        self.collection_name = "creator_marketing"
        self.vectorstore = None
        
    def initialize_vectorstore(self):
        """Initialize or load existing vectorstore"""
        try:
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
            logger.info(f"✅ Initialized vectorstore: {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ Error initializing vectorstore: {e}")
            raise
    
    def load_creator_marketing_data(self) -> bool:
        """
        Load creator marketing data from resource folder into the vector store.
        Clears existing data first, then loads all files from resource folder.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("🔄 Starting creator marketing data loading...")
            
            if not self.vectorstore:
                self.initialize_vectorstore()
            
            # Step 1: Clear all existing data from the database
            logger.info("🗑️ Clearing existing data from database...")
            success_clear = self.clear_collection()
            if not success_clear:
                logger.warning("⚠️ Failed to clear existing data, continuing anyway...")
            
            # Step 2: Load data from resource folder
            all_docs = []
            
            # Load from resource folder (all file types)
            resource_docs = self._load_from_resource_folder()
            all_docs.extend(resource_docs)
            
            # Also load predefined knowledge base as fallback
            if len(all_docs) == 0:
                logger.info("📚 No files found in resource folder, loading predefined knowledge...")
                knowledge_docs = self._load_predefined_knowledge()
                all_docs.extend(knowledge_docs)
            
            if not all_docs:
                logger.warning("⚠️  No documents were loaded")
                return False
            
            # Step 3: Process and store documents
            success = self._process_and_store_documents(all_docs)
            
            if success:
                logger.info("✅ Creator marketing data loading completed successfully")
                logger.info(f"📊 Loaded {len(all_docs)} documents total")
            else:
                logger.error("❌ Failed to process and store documents")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error during creator marketing data loading: {e}", exc_info=True)
            return False
    
    def _load_predefined_knowledge(self) -> List[Document]:
        """Load predefined creator marketing knowledge base"""
        logger.info("📚 Loading predefined creator marketing knowledge...")
        
        knowledge_data = []
        documents = []
        for item in knowledge_data:
            doc = Document(
                page_content=f"Title: {item['title']}\n\n{item['content']}",
                metadata={
                    "source": "predefined_knowledge",
                    "title": item["title"],
                    "category": item["category"],
                    "tags": item["tags"]
                }
            )
            documents.append(doc)
        
        logger.info(f"✅ Loaded {len(documents)} predefined knowledge documents")
        return documents
    def _load_from_resource_folder(self) -> List[Document]:
        """Load all files from the resource folder"""
        documents = []
        resource_dir = Path("./resource")
        
        if not resource_dir.exists():
            logger.info("📁 Resource directory not found, creating it...")
            resource_dir.mkdir(parents=True, exist_ok=True)
            logger.info("📁 Created ./resource directory - please add your files there")
            return documents
        
        logger.info(f"📂 Loading files from resource directory: {resource_dir}")
        
        # Load different file types (using TextLoader for markdown to avoid unstructured dependency)
        file_types = {
            "**/*.md": TextLoader,
            "**/*.txt": TextLoader,
            "**/*.pdf": PyPDFLoader
        }
        
        for pattern, loader_cls in file_types.items():
            try:
                loader = DirectoryLoader(
                    str(resource_dir),
                    glob=pattern,
                    loader_cls=loader_cls
                )
                docs = loader.load()
                
                # Enrich metadata
                for doc in docs:
                    doc.metadata['source'] = 'resource_file'
                    doc.metadata['file_type'] = pattern.split('.')[-1]
                    doc.metadata['file_path'] = doc.metadata.get('source', 'unknown')
                
                documents.extend(docs)
                if docs:
                    logger.info(f"✅ Loaded {len(docs)} {pattern} files")
                
            except Exception as e:
                logger.error(f"❌ Error loading {pattern} files: {e}")
        
        logger.info(f"📊 Total files loaded from resource folder: {len(documents)}")
        return documents

    
    def _load_markdown_files(self) -> List[Document]:
        """Load markdown files from data directory"""
        documents = []
        data_dir = Path("./data/creator_marketing")
        
        if not data_dir.exists():
            logger.info("📁 Creator marketing data directory not found, skipping markdown files")
            return documents
        
        try:
            loader = DirectoryLoader(
                str(data_dir),
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader
            )
            docs = loader.load()
            
            # Enrich metadata
            for doc in docs:
                doc.metadata['source'] = 'markdown_file'
                doc.metadata['file_path'] = doc.metadata.get('source', 'unknown')
            
            documents.extend(docs)
            logger.info(f"✅ Loaded {len(docs)} markdown documents")
            
        except Exception as e:
            logger.error(f"❌ Error loading markdown files: {e}")
        
        return documents
    
    def _load_text_files(self) -> List[Document]:
        """Load text files from data directory"""
        documents = []
        data_dir = Path("./data/creator_marketing")
        
        if not data_dir.exists():
            logger.info("📁 Creator marketing data directory not found, skipping text files")
            return documents
        
        try:
            loader = DirectoryLoader(
                str(data_dir),
                glob="**/*.txt",
                loader_cls=TextLoader
            )
            docs = loader.load()
            
            # Enrich metadata
            for doc in docs:
                doc.metadata['source'] = 'text_file'
                doc.metadata['file_path'] = doc.metadata.get('source', 'unknown')
            
            documents.extend(docs)
            logger.info(f"✅ Loaded {len(docs)} text documents")
            
        except Exception as e:
            logger.error(f"❌ Error loading text files: {e}")
        
        return documents
    
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
                self.vectorstore.add_documents(batch)
            
            logger.info("✅ All documents processed and stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing documents: {e}")
            return False
    
    def search_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in the vector store.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            if not self.vectorstore:
                self.initialize_vectorstore()
            
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": 1 - score  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error searching documents: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            if not self.vectorstore:
                self.initialize_vectorstore()
            
            collection_data = self.vectorstore.get()
            
            return {
                "collection_name": self.collection_name,
                "document_count": len(collection_data['ids']),
                "status": "active" if len(collection_data['ids']) > 0 else "empty"
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "document_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection"""
        try:
            if not self.vectorstore:
                self.initialize_vectorstore()
            
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(self.collection_name)
            self.initialize_vectorstore()
            
            logger.info("✅ Collection cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing collection: {e}")
            return False