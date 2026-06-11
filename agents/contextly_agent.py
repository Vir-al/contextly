"""
Contextly Agent

A unified intelligent assistant that combines Notion, Slack, and Jira tools
to provide comprehensive answers with context, resources, and actionable insights.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple,Union
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
import asyncio
from datetime import datetime
from langchain_core.runnables import Runnable

# Import your existing tools
from tools.notion_tool import NotionTool
from tools.slack_tool import SlackTool  
from tools.jira_tool import JiraTool

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextlyAgent:
    """
    Unified agent that intelligently routes queries across Notion, Slack, and Jira
    to provide comprehensive, context-rich responses with actionable insights.
    """
    
    def __init__(self, llm:ChatGoogleGenerativeAI,embedding_model:GoogleGenerativeAIEmbeddings):
        """Initialize the Contextly Agent with all integrated tools."""
    
        self.llm = llm
        self.embedding_model = embedding_model
        # Initialize individual tools
        self.notion_tool = NotionTool(llm, embedding_model)
        self.slack_tool = SlackTool(llm, embedding_model)
        self.jira_tool = JiraTool(llm)
        
        # Create the unified agent
        self.agent_executor = self._create_unified_agent()
        
        logger.info("🚀 Contextly Agent initialized successfully")
    
    def _create_unified_agent(self) -> Runnable:
        """Create a unified agent that can use all available tools."""
        
        # Collect all available tools
        # Create the agent prompt
        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("ai", "{agent_scratchpad}"),
        ])
        
        # Create the agent
        return create_react_agent(
            self.llm,
            self.get_tools(),
            agent_prompt,
        )
    
    def get_tools(self) -> List[Tool]:
        tools: List[Tool] = []

        for tool in self._normalize_tool(self.notion_tool.get_tool()):
            tools.append(tool)
        for tool in self._normalize_tool(self.slack_tool.get_tool()):
            tools.append(tool)
        for tool in self._normalize_tool(self.jira_tool.get_tool()):
            tools.append(tool)

        tools.append(self._create_synthesis_tool())
        return tools
    
    def _normalize_tool(self, tool_or_list: Union[Tool, List[Tool]]) -> List[Tool]:
        return tool_or_list if isinstance(tool_or_list, list) else [tool_or_list]

    def _get_system_prompt(self) -> str:
        """Get the comprehensive system prompt for the unified agent."""
        return """
        You are Contextly, an intelligent and resourceful workplace assistant.

        **Core Objective:**
        Your mission is to provide a single, unified, and comprehensive answer by intelligently querying and synthesizing information from Notion (for documentation, plans, policies), Slack (for recent conversations, informal decisions), and Jira (for project tasks, status, and sprints). You are the bridge between these systems.

        **Operational Protocol:**
        You must operate in a clear, multi-step process for every query:
        1.  **Deconstruct & Strategize:** First, understand the user's intent. Identify the key entities (project names, feature titles, people, etc.). Formulate a plan on which tools to use. A single question might require looking in multiple places. For example, a question about a "feature delay" might require checking Jira for the ticket status AND Slack for recent discussions about blockers.
        2.  **Execute & Gather:** Use the available tools sequentially to gather evidence. Start with the tool most likely to hold the primary answer.
        3.  **Synthesize & Conclude:** Do not just output the raw data from a tool. Your primary value is in synthesizing the findings. If you use multiple tools, combine their outputs into a single, easy-to-read narrative.
        4.  **Cite Your Sources:** When presenting the final answer, briefly mention where the information came from (e.g., "According to Jira ticket PROJECT-123...", "In a Slack discussion in the #engineering channel...", "The project plan in Notion states..."). This builds trust and allows users to dig deeper.

        **Tool Usage Strategy:**
        - Use **Notion** (`SearchNotionWorkspace`) for formal documentation: project plans, specifications, meeting notes, company policies, and official roadmaps.
        - Use **Slack** (`SearchSlackHistory`) for informal context: recent discussions, real-time updates, team sentiment, and quick decisions that haven't been formalized yet.
        - Use **Jira** (`JiraOperations`) for structured work tracking: ticket status, sprint progress, bug reports, assigned tasks, and blockers.
        - If a tool returns no information, acknowledge it and try another relevant tool if your strategy allows for it.
        - The **SynthesizeInformation** tool is for meta-analysis. Use it ONLY when the user asks a broad question about the available data itself (e.g., "What can you tell me?", "Summarize your knowledge sources") or as a final step to provide a summary if requested. Do NOT use it for specific queries about projects or tasks.

        **Response Formatting:**
        Always follow the Thought/Action/Action Input/Observation chain. When you have gathered all necessary information and have synthesized it, provide the final, user-facing answer.

        **Example Flow:**
        Question: Is the "New User Onboarding" feature delayed and who is talking about it?
        Thought: The user is asking about a feature's status and related discussions. I should first check Jira for the official status and then search Slack for any recent conversations about delays.
        Action: JiraOperations
        Action Input: "status of 'New User Onboarding' feature"
        ...
        Observation: (Jira output shows the feature is 'Blocked')
        ...
        Thought: Now that I know the feature is blocked, I need to find the context in Slack.
        Action: SearchSlackHistory
        Action Input: "'New User Onboarding' delay OR blocked"
        ...
        Observation: (Slack output shows a conversation between two engineers about an API issue)
        ...
        Thought: I have all the information I need. I have the status from Jira and the context from Slack. I can now synthesize this into a final answer.
        Final Answer: The "New User Onboarding" feature is currently marked as 'Blocked' in Jira (Ticket-ID: UX-451). Recent Slack conversations in the #dev channel suggest the block is due to an unexpected API dependency issue being discussed by Alice and Bob.

        **Handling Vague Inputs:**
        If the user input is vague or just a greeting (e.g., "hi", "hello"), do not use any tools. Instead, respond helpfully and state your purpose.
        Thought: The user's input is a simple greeting. I should introduce myself and guide them on how to use me.
        Final Answer: Hi there! I’m Contextly. I can connect to Notion, Slack, and Jira to answer your questions about projects, discussions, and documentation. What would you like to know?

        TOOLS:
        ------
        {tools}

        Available tool names: {tool_names}
        """

    def _create_synthesis_tool(self) -> Tool:
        """Create a tool for synthesizing information across sources."""
        
        def synthesize_information(query: str) -> str:
            """Synthesize and analyze information patterns across all sources."""
            try:
                # Get collection stats
                notion_count = self.notion_tool.get_collection_count()
                slack_count = self.slack_tool.get_collection_count()
                
                synthesis = f"""
**Information Synthesis for: "{query}"**

📊 **Data Sources Status:**
- Notion Documents: {notion_count:,} indexed
- Slack Messages: {slack_count:,} indexed
- Jira Integration: ✅ Available

🔍 **Cross-Reference Analysis:**
This synthesis combines insights from multiple sources to provide comprehensive context.

💡 **Key Insights:**
- Information span across {notion_count + slack_count:,} total knowledge items
- Multi-platform context ensures complete picture
- Real-time and historical data integration

📈 **Recommendations:**
- Verify findings across multiple sources when possible
- Check for recent updates in Slack discussions
- Review related Jira tickets for current status
- Consider reaching out to key stakeholders for clarification

⏰ **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                return synthesis
                
            except Exception as e:
                logger.error(f"Error in synthesis: {e}")
                return f"Error during information synthesis: {str(e)}"
        
        return Tool(
            name="SynthesizeInformation",
            func=synthesize_information,
            description=(
                "Use this tool to provide meta-analysis and synthesis of information "
                "across all available sources. Useful for understanding data coverage "
                "and providing comprehensive context."
            )
        )
    
   