"""
MCP Client Integration
Wrapper for langchain_mcp_adapters.client.MultiServerMCPClient
"""

import logging
from typing import Dict, List, Any, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class ContextlyMCPClient:
    """MCP client integration for Contextly."""
    
    def __init__(self, servers_config: Dict[str, Any], llm):
        """
        Initialize MCP client with server configurations.
        
        Args:
            servers_config: Dictionary of server configurations
            llm: Language model instance for the agent
        """
        self.servers_config = servers_config
        self.llm = llm
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List[BaseTool] = []
        self.agent = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the MCP client and tools."""
        if self._initialized:
            return True
            
        try:
            if not self.servers_config:
                logger.info("No MCP servers configured")
                return False
                
            logger.info(f"Initializing MCP client with servers: {list(self.servers_config.keys())}")
            
            # Create the MCP client
            self.client = MultiServerMCPClient(self.servers_config)
            
            # Get available tools
            self.tools = await self.client.get_tools()
            logger.info(f"Retrieved {len(self.tools)} MCP tools")
            
            # Create the react agent with MCP tools
            if self.tools:
                self.agent = create_react_agent(self.llm, self.tools)
                logger.info("MCP React agent created successfully")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}", exc_info=True)
            return False
    
    async def process_query(self, query: str) -> str:
        """
        Process a query using MCP tools.
        
        Args:
            query: The user query to process
            
        Returns:
            Response from the MCP agent
        """
        if not self._initialized:
            await self.initialize()
            
        if not self.agent:
            return "MCP agent not available"
            
        try:
            logger.info(f"Processing MCP query: {query}")
            response = await self.agent.ainvoke({"messages": [{"role": "user", "content": query}]})
            
            # Extract the response content
            if isinstance(response, dict) and "messages" in response:
                messages = response["messages"]
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        return last_message.content
                    elif isinstance(last_message, dict) and 'content' in last_message:
                        return last_message['content']
            
            return str(response)
            
        except Exception as e:
            logger.error(f"Error processing MCP query: {e}", exc_info=True)
            return f"Error processing MCP query: {str(e)}"
    
    def get_available_tools(self) -> List[str]:
        """Get list of available MCP tool names."""
        if not self.tools:
            return []
        return [tool.name for tool in self.tools if hasattr(tool, 'name')]
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get status of MCP servers and tools."""
        return {
            "initialized": self._initialized,
            "servers_configured": list(self.servers_config.keys()),
            "tools_count": len(self.tools),
            "available_tools": self.get_available_tools(),
            "agent_ready": self.agent is not None
        }
    
    async def close(self):
        """Close MCP client connections."""
        if self.client:
            try:
                # Close client connections if available
                if hasattr(self.client, 'close'):
                    await self.client.close()
                logger.info("MCP client connections closed")
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")