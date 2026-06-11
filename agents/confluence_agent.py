"""
Confluence Agent
Handles queries related to official documentation and processes.
"""

import logging
from typing import Dict, Any
from tools.confluence_tool import ConfluenceTool

logger = logging.getLogger(__name__)

class ConfluenceAgent:
    """Agent specialized in handling Confluence documentation queries."""
    
    def __init__(self, confluence_tool: ConfluenceTool):
        self.confluence_tool = confluence_tool
    
    def process_query(self, question: str) -> str:
        """
        Process a query related to Confluence documentation.
        
        Args:
            question: The user's question
            
        Returns:
            Response from Confluence search with sources
        """
        try:
            logger.info(f"Processing Confluence query: {question[:50]}...")
            
            # Search Confluence using the tool
            result = self.confluence_tool.get_tool().func(question)
            
            logger.info("Confluence query processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Confluence query: {e}")
            return f"Sorry, I encountered an error searching the documentation: {str(e)}"
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get status information about the Confluence collection.
        
        Returns:
            Dictionary with collection status information
        """
        try:
            count = self.confluence_tool.get_collection_count()
            return {
                "collection_name": "Confluence Documentation",
                "document_count": count,
                "status": "active" if count > 0 else "empty"
            }
        except Exception as e:
            logger.error(f"Error getting Confluence collection status: {e}")
            return {
                "collection_name": "Confluence Documentation",
                "document_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def suggest_queries(self) -> list:
        """
        Suggest example queries that this agent can handle.
        
        Returns:
            List of example query strings
        """
        return [
            "How do I deploy the application?",
            "What is the code review process?",
            "Show me the API documentation",
            "What are the security guidelines?",
            "How do I set up the development environment?",
            "What is the release process?",
            "Show me the architecture documentation",
            "What are the coding standards?"
        ]