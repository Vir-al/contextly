"""
MCP Agent
Agent that integrates with MCP (Model Context Protocol) servers to provide additional tools and capabilities.
"""

import logging
from typing import Dict, Any, Optional
from core.mcp_client import ContextlyMCPClient

logger = logging.getLogger(__name__)

class MCPAgent:
    """Agent for handling MCP (Model Context Protocol) interactions."""
    
    def __init__(self, mcp_client: ContextlyMCPClient):
        """
        Initialize MCP agent.
        
        Args:
            mcp_client: Initialized MCP client instance
        """
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)
    
    async def process_query(self, query: str) -> str:
        """
        Process a query using MCP tools.
        
        Args:
            query: The user query to process with MCP tools
            
        Returns:
            Response from MCP tools or error message
        """
        try:
            self.logger.info(f"Processing MCP query: {query}")
            
            # Ensure MCP client is initialized
            if not self.mcp_client._initialized:
                await self.mcp_client.initialize()
            
            if not self.mcp_client.tools:
                return "MCP tools are not available. Please check your MCP server configuration."
            
            # Process the query through MCP tools
            response = await self.mcp_client.process_query(query)
            
            self.logger.info("MCP query processed successfully")
            return response
            
        except Exception as e:
            error_msg = f"Error processing MCP query: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return error_msg
    
    def get_available_tools(self) -> Dict[str, str]:
        """
        Get information about available MCP tools.
        
        Returns:
            Dictionary containing tool information
        """
        try:
          
            return {tool.name: tool.description for tool in self.mcp_client.tools}
    
        except Exception as e:
            self.logger.error(f"Error getting MCP tools info: {e}")
            return {
                "available_tools": [],
                "server_status": {"error": str(e)},
                "tools_count": 0
            }
    
    def is_available(self) -> bool:
        """Check if MCP agent is available and ready."""
        return (
            self.mcp_client is not None and 
            self.mcp_client._initialized and 
            self.mcp_client.agent is not None
        )
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get detailed integration status for MCP."""
        try:
            status = self.mcp_client.get_server_status()
            return {
                "enabled": self.is_available(),
                "details": status
            }
        except Exception as e:
            return {
                "enabled": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close MCP agent and client connections."""
        try:
            if self.mcp_client:
                await self.mcp_client.close()
            self.logger.info("MCP agent closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing MCP agent: {e}")