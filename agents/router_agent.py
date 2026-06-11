import json
import logging
from typing import Dict, Any

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.mcp_agent import MCPAgent

logger = logging.getLogger(__name__)


class RouterAgent:
    """Intelligent router that analyzes queries and directs them to appropriate agents."""

    SYSTEM_PROMPT = """
You are Contextly's intelligent router, a sophisticated AI assistant. Your primary function is to analyze user queries and route them to the most appropriate tool or agent based on the query's intent. You must respond ONLY with a single, valid JSON object.

## Your Task

1.  **Analyze the User's Query**: Carefully examine the user's message to understand their underlying intent.
2.  **Evaluate Key Factors**: Determine the best destination based on the following:
    * **Recency**: Is the user asking for the absolute latest information (favoring Slack) or established knowledge (favoring Confluence)?
    * **Formality**: Is this related to official, documented processes (Confluence) or informal, real-time chats (Slack)?
    * **Context Type**: Is the query about tasks and project management (Jira), documentation (Confluence), conversations (Slack), or requires a specialized MCP tool?
3.  **Select the Destination**: Choose the single best destination from the "Tools Available" list below.
4.  **Formulate the Reasoning**: In one brief sentence, explain *why* you chose that destination.
5.  **Construct the JSON Response**: Combine the destination and reasoning into the specified JSON format.

**Here are more mcp tools you can use if mcp server
**MCP**
{mcp_tools}

## Tools Available

* **`confluence`**: Use for queries about official documentation, established processes, "how-to" guides, architectural decisions, and formal procedures. It's the source of truth for "how things are done."
* **`slack`**: Use for queries about recent team conversations, informal decisions, real-time discussions, ad-hoc updates, and to understand "what's the latest on..." a topic.
* **`jira`**: Use for all actions related to project tasks, including creating, updating, or querying tickets, checking sprint progress, identifying blockers, and managing workflows.
* **`mcp`**: Use for specialized actions that require executing a specific tool from the MCP toolkit.
* **`end`**: **Use for simple interactions (greetings, thank yous) or when the user's query is too ambiguous or directly asks for "help". This allows you to respond directly with a clarifying message instead of routing to a tool.**

Examples:

- "How do I deploy the app?" -> {{"destination": "confluence", "reasoning": "Official deployment process documentation"}}
- "What did John say about the API?" -> {{"destination": "slack", "reasoning": "Recent informal team conversation"}}
- "Create a bug ticket" -> {{"destination": "jira", "reasoning": "Ticket creation and project management"}}
- "What's blocking our sprint?" -> {{"destination": "jira", "reasoning": "Sprint progress and blocker identification"}}
- "Any call which need mcp tool user " -> {{"destination": "mcp", "reasoning": "Using MCP tools with reason"}}
- "Hello" -> {{"destination": "end", "reasoning": "Simple greeting, no tools needed"}}
"""

    def __init__(self, llm: ChatGoogleGenerativeAI,mcp_agent:MCPAgent):
        self.llm = llm
        self.mcp_agent = mcp_agent

    def _generate_mcp_tool_prompt(self) -> str:
        """
        Generates the system prompt, dynamically including available MCP tools.
        """
        mcp_tool_descriptions = self.mcp_agent.get_available_tools()

        if not mcp_tool_descriptions:
         return "No MCP tools found."
        
        mcp_prompt_part = ""
        if mcp_tool_descriptions:
            mcp_prompt_part += "\n**MCP (Model Context Protocol) Tools:**\n"
            for tool_name, tool_description in mcp_tool_descriptions.items():
                mcp_prompt_part += f'- **{tool_name}**: {tool_description}\n'
        
        return mcp_prompt_part
    

    def route_query(self, question: str) -> Dict[str, Any]:
        """
        Analyze a query and determine the appropriate routing destination.
        """
        try:
 
            system_prompt_for_mcp = self._generate_mcp_tool_prompt()
            final_system_prompt = self.SYSTEM_PROMPT.format(mcp_tools=system_prompt_for_mcp)

            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(final_system_prompt),
                HumanMessagePromptTemplate.from_template("Query: {question}")
            ])
            prompt = prompt_template.format_prompt(
                question=question
            )
            response = self.llm.invoke(prompt.to_messages())

            logger.debug(f"Router LLM raw response: {response.content}")
            
            json_string = response.content.strip()
            if json_string.startswith("```json"):
                json_string = json_string[len("```json"):].strip()
            if json_string.endswith("```"):
                json_string = json_string[:-len("```")].strip()

            route_decision = json.loads(json_string)

            # Validate required fields
            if "destination" not in route_decision:
                raise ValueError("Missing 'destination' key in routing decision")

            destination = route_decision.get("destination")
            args = route_decision.get("args", {})
            reasoning = route_decision.get("reasoning", "")

            valid_destinations = {"confluence", "slack", "jira", "mcp", "end"}
            if destination not in valid_destinations:
                logger.warning(f"❌ Invalid destination: {destination}")
                destination = "end"

            logger.info(f"📌 Routed query to: {destination} — Reason: {reasoning}")
            return {"destination": destination, "args": args, "reasoning": reasoning}

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse router JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Error in route_query: {e}", exc_info=True)

        # Fallback
        return {"destination": "end", "args": {}, "reasoning": "Failed to route, fallback to 'end'"}

 