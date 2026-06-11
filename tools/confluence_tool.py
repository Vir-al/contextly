"""
Confluence Tool
Handles searching and retrieving information from Confluence documentation.
"""

import os
import logging
from typing import Dict, Any
from langchain.agents import Tool
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class ConfluenceTool:
    """Tool for searching Confluence documentation using ChromaDB vector store."""
    
    def __init__(self, llm: ChatGoogleGenerativeAI, embedding_model: GoogleGenerativeAIEmbeddings):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vectorstore = self._initialize_vectorstore()
        self.tool = self._create_tool()
    
    def _initialize_vectorstore(self) -> Chroma:
        """Initialize the Confluence ChromaDB vector store."""
        chroma_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        collection_name = os.getenv("CONFLUENCE_COLLECTION", "contextly_confluence")
        
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=f"{chroma_dir}/confluence"
        )
    
    def _format_results_with_sources(self, result: Dict[str, Any]) -> str:
        """Format QA results with source attribution."""
        answer = result.get('result', "No answer found.")
        source_docs = result.get('source_documents', [])
        references = {doc.metadata.get('source_url', 'Source not available') for doc in source_docs}
        
        if references:
            sources_text = "\n".join([f"- {ref}" for ref in references])
            return f"Answer: {answer}\n\nSources:\n{sources_text}"
        return f"Answer: {answer}"
    
    def _search_confluence(self, query: str) -> str:
        """Search Confluence documentation."""
        try:
            retriever = self.vectorstore.as_retriever()
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=retriever,
                chain_type="stuff",
                return_source_documents=True
            )
            result = qa_chain.invoke(query)
            return self._format_results_with_sources(result)
        except Exception as e:
            logger.error(f"Error searching Confluence: {e}")
            return f"Error searching Confluence documentation: {str(e)}"
    
    def _create_tool(self) -> Tool:
        """Create the Confluence search tool."""
        return Tool(
            name="SearchConfluence",
            func=self._search_confluence,
            description=(
                "Use for questions about official documentation, company processes, "
                "how-to guides, project plans, and formal knowledge stored in Confluence."
            )
        )
    
    def get_tool(self) -> Tool:
        """Get the Confluence tool instance."""
        return self.tool
    
    def add_documents(self, documents: list):
        """Add documents to the Confluence vector store."""
        try:
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()
            logger.info(f"Added {len(documents)} documents to Confluence collection")
        except Exception as e:
            logger.error(f"Error adding documents to Confluence: {e}")
            raise
    
    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0