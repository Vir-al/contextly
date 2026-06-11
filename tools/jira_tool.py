"""
Jira Tool
Handles Jira ticket operations and integrations.
"""

import logging
from langchain_core.tools import BaseTool
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_community.agent_toolkits.jira.toolkit import JiraToolkit
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class JiraTool:
    """Tool for Jira ticket operations and project management."""
    
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.jira_wrapper = JiraAPIWrapper()
        self.jira_executor = None
        self.jira_toolkit = JiraToolkit.from_jira_api_wrapper(self.jira_wrapper)
        
    def get_tool(self) -> list[BaseTool]:
        """Get the Jira tool instance."""
        return self.jira_toolkit.get_tools()
