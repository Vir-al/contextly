"""
LangGraph Workflow
Orchestrates the multi-agent workflow for Contextly.
"""

import json
import logging
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .response_models import GraphState, ContextlyResponse
from agents.router_agent import RouterAgent
from agents.confluence_agent import ConfluenceAgent
from agents.slack_agent import SlackAgent
from agents.jira_agent import JiraAgent
from agents.mcp_agent import MCPAgent

logger = logging.getLogger(__name__)

class ContextlyWorkflow:
    """LangGraph workflow orchestrator for Contextly multi-agent system."""

    def __init__(
        self,
        llm: ChatGoogleGenerativeAI,
        confluence_agent: ConfluenceAgent,
        slack_agent: SlackAgent,
        jira_agent: JiraAgent,
        mcp_agent: MCPAgent = None
    ):
        self.llm = llm
        self.router_agent = RouterAgent(llm,mcp_agent)
        self.confluence_agent = confluence_agent
        self.slack_agent = slack_agent
        self.jira_agent = jira_agent
        self.mcp_agent = mcp_agent

        self.workflow = self._build_workflow()
        self.agent_graph = self.workflow.compile(checkpointer=MemorySaver())

    def _router_node(self, state: GraphState) -> Dict[str, Any]:
        """Router node that determines which agent should handle the query."""
        logger.info("Routing query...")
        try:
            route_decision = self.router_agent.route_query(
                state['question']
            )
            logger.info(f"Routing decision: {route_decision}")
            return {
                "route_destination": route_decision["destination"],
                "route_args": route_decision["args"]
            }
        except Exception as e:
            logger.error(f"Error in router node: {e}")
            return {
                "route_destination": "end",
                "route_args": {}
            }

    def _confluence_agent_node(self, state: GraphState) -> Dict[str, Any]:
        """Process query using Confluence agent."""
        logger.info("Processing with Confluence agent...")
        try:
            result = self.confluence_agent.process_query(
                state['question']
            )
            return {"confluence_search_results": result}
        except Exception as e:
            logger.error(f"Error in confluence agent node: {e}")
            return {"confluence_search_results": f"Error processing Confluence query: {str(e)}"}

    def _slack_agent_node(self, state: GraphState) -> Dict[str, Any]:
        """Process query using Slack agent."""
        logger.info("Processing with Slack agent...")
        try:
            result = self.slack_agent.process_query(
                state['question']
            )
            return {"slack_search_results": result}
        except Exception as e:
            logger.error(f"Error in slack agent node: {e}")
            return {"slack_search_results": f"Error processing Slack query: {str(e)}"}

    def _jira_agent_node(self, state: GraphState) -> Dict[str, Any]:
        """Process query using Jira agent."""
        logger.info("Processing with Jira agent...")
        try:
            result = self.jira_agent.process_query(
                state['question']
            )
            return {"jira_results": result}
        except Exception as e:
            logger.error(f"Error in jira agent node: {e}")
            return {"jira_results": f"Error processing Jira query: {str(e)}"}

    async def _mcp_agent_node(self, state: GraphState) -> Dict[str, Any]:
        """Process query using MCP agent."""
        logger.info("Processing with MCP agent...")
        try:
            if not self.mcp_agent or not self.mcp_agent.is_available():
                return {"mcp_results": "MCP agent is not available or configured"}
            
            result = await self.mcp_agent.process_query(
                state['question']
            )
            return {"mcp_results": result}
        except Exception as e:
            logger.error(f"Error in mcp agent node: {e}")
            return {"mcp_results": f"Error processing MCP query: {str(e)}"}

    def _generate_final_answer_node(self, state: GraphState) -> Dict[str, Any]:
        """Generate the final synthesized response using a PydanticOutputParser."""
        logger.info("Generating final answer...")
        try:
            # Setup the parser with the desired response model.
            parser = PydanticOutputParser(pydantic_object=ContextlyResponse)
            
            # Get related conversation context for better responses
            related_context = ""
            try:
                related_context = self.slack_agent.get_related_context(state['question'], 5)
            except Exception as e:
                logger.warning(f"Could not get related context: {e}")

            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                You are Contextly - an AI assistant that brings relevant context to teams when and where they need it.

                Your goal is to synthesize information from multiple sources into actionable insights that help teams stay aligned and move faster.

                **Response Guidelines:**
                - Lead with the most relevant context for the user's immediate need
                - Highlight connections between different information sources when available
                - Surface potential blockers or dependencies proactively
                - Include relevant people/stakeholders when appropriate
                - Provide clear next steps or actions when applicable
                - Keep responses concise but comprehensive
                - Focus on helping teams stay aligned and reduce friction
                - Use related conversation context to provide more relevant and contextual responses

                **Context Synthesis Priorities:**
                1. Answer the immediate question directly
                2. Provide related context that might be helpful
                3. Highlight any inconsistencies or gaps in information
                4. Suggest relevant people to talk to when mentioned in sources
                5. Recommend follow-up actions or next steps
                6. Reference related conversations when relevant to the query

                {format_instructions}
                """),
                ("user", "Query: {q}\nConfluence Results: {c}\nSlack Results: {s}\nJira Results: {j}\nMCP Results: {m}"),
            ])
            
            # Create a chain that pipes the prompt, LLM, and parser together.
            chain = prompt | self.llm | parser

            # Invoke the chain with the current state and format instructions.
            format_instructions = ContextlyResponse.model_json_schema()

            response_model = chain.invoke({
                "format_instructions": format_instructions,
                "q": state['question'],
                "rc": related_context,
                "c": state.get('confluence_search_results', 'Not used.'),
                "s": state.get('slack_search_results', 'Not used.'),
                "j": state.get('jira_results', 'Not used.'),
                "m": state.get('mcp_results', 'Not used.')
            })

            # Convert the Pydantic model to a dictionary for the state.
            final_response_dict = response_model.dict()
            final_response_dict['agent_used'] = state.get('route_destination', 'unknown')

            return {"final_response": final_response_dict}

        except Exception as e:
            logger.error(f"Error generating final answer: {e}")
            return {
                "final_response": {
                    "summary": f"I encountered an error processing your request: {str(e)}",
                    "agent_used": "error"
                }
            }

    def _decide_next_node(self, state: GraphState) -> str:
        """
        Conditional routing logic that reads the destination from the state.
        This function determines which node to go to next based on the router's output.
        """
        destination = state.get("route_destination")
        logger.info(f"Deciding next node. Destination: '{destination}'")

        if destination == "slack":
            return "slack_agent"
        elif destination == "confluence":
            return "confluence_agent"
        elif destination == "jira":
            return "jira_agent"
        elif destination == "mcp":
            return "mcp_agent"
        else:
            # If the destination is "end", "error", or anything else,
            # we proceed to the final answer generator.
            return "final_answer_generator"

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("confluence_agent", self._confluence_agent_node)
        workflow.add_node("slack_agent", self._slack_agent_node)
        workflow.add_node("jira_agent", self._jira_agent_node)
        workflow.add_node("mcp_agent", self._mcp_agent_node)
        workflow.add_node("final_answer_generator", self._generate_final_answer_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add conditional edges from the router. The `_decide_next_node` function
        # will return the name of the next node to execute.
        workflow.add_conditional_edges(
            "router",
            self._decide_next_node,
            {
                "slack_agent": "slack_agent",
                "confluence_agent": "confluence_agent",
                "jira_agent": "jira_agent",
                "mcp_agent": "mcp_agent",
                # If _decide_next_node returns "final_answer_generator", it will go there.
                "final_answer_generator": "final_answer_generator"
            }
        )

        # After each agent runs, the flow proceeds to the final answer generator.
        workflow.add_edge("slack_agent", "final_answer_generator")
        workflow.add_edge("confluence_agent", "final_answer_generator")
        workflow.add_edge("jira_agent", "final_answer_generator")
        workflow.add_edge("mcp_agent", "final_answer_generator")
        
        # The graph ends after the final answer is generated.
        workflow.add_edge("final_answer_generator", END)

        return workflow

    async def process_query(
        self,
        question: str,
        user_id: str,
        thread_ts:str
    ) -> ContextlyResponse:
        """
        Process a user query through the workflow.
        The routing logic is now handled entirely within the graph.
        """
        try:
            initial_state = {
                "question": question,
                "user_id": user_id
            }

            # **FIX:** Added config to provide a thread_id for the checkpointer.
            # This is required for MemorySaver to persist conversation state.
            # We'll use the user_id to ensure each user has a unique thread.
            config = {"configurable": {"thread_id": thread_ts}}
            
            # Invoke the graph with the initial state and the config.
            final_state = await self.agent_graph.ainvoke(initial_state, config=config)

            # Return the structured response from the final state.
            return ContextlyResponse(**final_state['final_response'])

        except Exception as e:
            logger.error(f"Error processing query through workflow: {e}", exc_info=True)
            return ContextlyResponse(
                summary=f"I encountered an error processing your request: {str(e)}",
                agent_used="error"
            )