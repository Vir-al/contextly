"""
Notion Tool
Handles searching and retrieving information from a vectorized Notion workspace.
"""

from datetime import datetime
import os
import logging
from typing import Dict, Any, List
from langchain.agents import Tool
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from client.notion_fetcher import NotionClient


# Initialize a logger for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotionTool:
    """Enhanced Notion tool with better search capabilities and response formatting."""
    
    def __init__(self, llm: ChatGoogleGenerativeAI, embedding_model: GoogleGenerativeAIEmbeddings):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vectorstore = self._initialize_vectorstore()
        self.tool = self._create_tool()
        self._last_search_metadata = {}
    
    def _initialize_vectorstore(self) -> Chroma:
        """Initialize the Notion ChromaDB vector store from a persistent directory."""
        chroma_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        collection_name = os.getenv("NOTION_COLLECTION", "contextly_notion")
        notion_chroma_path = os.path.join(chroma_dir, "notion")
        
        logger.info(f"Initializing Notion vector store from: {notion_chroma_path}")
        
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=notion_chroma_path
        )
    
    async def index_workspace(self, notion_client:NotionClient):
        """Enhanced workspace indexing with better error handling and progress tracking."""
        logger.info("🔄 Starting enhanced Notion workspace indexing...")
        
        try:
            # Fetch workspace data
            workspace_data = await notion_client.get_workspace_content()
            all_pages = workspace_data.get("pages", [])
            
            # Include database pages
            for db in workspace_data.get("databases", []):
                all_pages.extend(getattr(db, 'pages', []))
            
            logger.info(f"📊 Found {len(all_pages)} pages to process")
            
            # Process pages with better error handling
            langchain_docs = []
            processed_count = 0
            failed_count = 0
            
            for i, page in enumerate(all_pages):
                try:
                    detailed_page = await notion_client.get_page(page.id, fetch_content=True)
                    
                    if not detailed_page.content_text or not detailed_page.content_text.strip():
                        logger.debug(f"Skipping empty page: {detailed_page.title}")
                        continue
                    
                    # Enhanced document creation with more metadata
                    doc = Document(
                        page_content=detailed_page.content_text,
                        metadata={
                            "page_id": detailed_page.id,
                            "page_url": str(detailed_page.url),
                            "page_title": detailed_page.title,
                            "parent_id": getattr(detailed_page.parent, 'id', None),
                            "parent_type": getattr(detailed_page.parent, 'type', None),
                            "last_edited": detailed_page.last_edited_time.isoformat(),
                            "created_time": detailed_page.created_time.isoformat(),
                            "content_length": len(detailed_page.content_text),
                            "indexed_at": datetime.now().isoformat(),
                            "source": "notion"
                        }
                    )
                    langchain_docs.append(doc)
                    processed_count += 1
                    
                    # Progress logging
                    if (i + 1) % 10 == 0:
                        logger.info(f"📈 Processed {i + 1}/{len(all_pages)} pages")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process page {page.id}: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"✅ Successfully processed {processed_count} pages, {failed_count} failed")
            
            if not langchain_docs:
                logger.warning("⚠️ No documents created from Notion. Aborting indexing.")
                return False
            
            # Enhanced text splitting
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
            )
            split_docs = text_splitter.split_documents(langchain_docs)
            logger.info(f"📄 Split {len(langchain_docs)} documents into {len(split_docs)} chunks")
            
            # Add to vector store
            if split_docs:
                self.add_documents(split_docs)
                logger.info("🎉 Notion workspace indexing complete!")
                return True
            else:
                logger.warning("⚠️ No chunks created after splitting")
                return False
                
        except Exception as e:
            logger.error(f"❌ Workspace indexing failed: {e}")
            return False
    
    def add_documents(self, documents: List[Document]):
        """Enhanced document addition with batch processing."""
        if not documents:
            logger.warning("No documents to add")
            return
        
        try:
            # Process in batches to avoid memory issues
            batch_size = 100
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                self.vectorstore.add_documents(batch)
                batch_num = (i // batch_size) + 1
                logger.info(f"📦 Added batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            self.vectorstore.persist()
            logger.info(f"💾 Successfully persisted {len(documents)} documents to Notion collection")
            
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
            raise
    
    def _search_notion(self, query: str) -> str:
        """Enhanced search with better context and formatting."""
        try:
            logger.info(f"🔍 Searching Notion for: {query}")
            
            # Enhanced retriever with more results
            retriever = self.vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    'k': 8,
                    'score_threshold': 0.2
                }
            )
            
            # Enhanced QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": ChatPromptTemplate.from_template("""
Use the following pieces of context from Notion documentation to answer the question. 
If you don't know the answer based on the context, say so clearly.

Context from Notion:
{context}

Question: {question}

Provide a comprehensive answer that includes:
1. Direct answer to the question
2. Supporting details from the documentation  
3. Any relevant context or background information
4. Related topics or next steps if applicable

Answer:""")
                }
            )
            
            result = qa_chain.invoke({"query": query})
            
            # Store metadata for potential follow-up
            self._last_search_metadata = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "sources_count": len(result.get('source_documents', []))
            }
            
            return self._format_results_with_sources(result)
            
        except Exception as e:
            logger.error(f"❌ Notion search error: {e}")
            return f"I encountered an error while searching Notion: {str(e)}. Please try rephrasing your question."
    
    def _format_results_with_sources(self, result: Dict[str, Any]) -> str:
        """Enhanced result formatting with better source attribution."""
        answer = result.get('result', "No answer found in the Notion workspace.")
        source_docs = result.get('source_documents', [])
        
        if not source_docs:
            return f"📚 **From Notion Documentation:**\n\n{answer}\n\n⚠️ *No specific sources found - this may be a general response.*"
        
        # Organize sources by page
        sources_by_page = {}
        for doc in source_docs:
            url = doc.metadata.get('page_url', 'URL not available')
            title = doc.metadata.get('page_title', 'Untitled Page')
            last_edited = doc.metadata.get('last_edited', 'Unknown date')
            
            if url not in sources_by_page:
                sources_by_page[url] = {
                    'title': title,
                    'last_edited': last_edited,
                    'chunks': 1
                }
            else:
                sources_by_page[url]['chunks'] += 1
        
        # Format response
        response = f"📚 **From Notion Documentation:**\n\n{answer}\n\n"
        
        if sources_by_page:
            response += "🔗 **Sources:**\n"
            for url, info in sources_by_page.items():
                chunks_text = f" ({info['chunks']} sections)" if info['chunks'] > 1 else ""
                response += f"- [{info['title']}]({url}){chunks_text}\n"
                response += f"  *Last updated: {info['last_edited'][:10]}*\n"
        
        response += f"\n⏰ *Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        
        return response
    
    def _create_tool(self) -> Tool:
        """Create the enhanced Notion search tool."""
        return Tool(
            name="SearchNotionWorkspace",
            func=self._search_notion,
            description=(
                "Search official Notion documentation and knowledge base. "
                "Best for: project plans, meeting notes, policies, procedures, "
                "official announcements, and documented processes. "
                "Returns comprehensive answers with source attribution."
            )
        )
    
    def get_tool(self) -> Tool:
        return self.tool
    
    def get_collection_count(self) -> int:
        """Get count of documents in collection."""
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get statistics about recent searches."""
        return {
            "last_search": self._last_search_metadata,
            "collection_size": self.get_collection_count()
        }