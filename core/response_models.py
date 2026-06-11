"""
Response Models
Data models for Contextly responses and state management.
"""

from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class ContextlyResponse(BaseModel):
    """Structured response model for Contextly bot responses."""
    
    summary: str = Field(
        description="Human-readable, well-structured response to the user's query."
    )
    references: Optional[List[str]] = Field(
        default=None,
        description="List of source URLs or references used to generate the response."
    )
    next_steps: Optional[str] = Field(
        default=None,
        description="Optional actionable next steps or recommendations for the user."
    )
    agent_used: Optional[str] = Field(
        default=None,
        description="Which agent was used to process this query (confluence, slack, jira, etc.)"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for the response (0.0 to 1.0)"
    )

class GraphState(TypedDict):
    """State object passed through the LangGraph workflow."""
    
    question: str
    user_id: str
    slack_search_results: str
    confluence_search_results: str
    jira_results: str
    final_response: ContextlyResponse
    route_destination: str
    route_args: dict

class AgentResult(BaseModel):
    """Result from individual agent processing."""
    
    agent_name: str = Field(description="Name of the agent that processed the query")
    result: str = Field(description="The agent's response")
    sources: Optional[List[str]] = Field(default=None, description="Sources used by the agent")
    success: bool = Field(description="Whether the agent processing was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")

class SystemStatus(BaseModel):
    """System health and status information."""
    
    status: str = Field(description="Overall system status (healthy, degraded, error)")
    integrations: dict = Field(description="Status of each integration")
    collections: dict = Field(description="Status of vector store collections")
    errors: Optional[List[str]] = Field(default=None, description="Any system errors")
    last_check: Optional[str] = Field(default=None, description="Timestamp of last health check")