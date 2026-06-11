"""
Slack Agent
Handles queries related to team conversations and informal discussions.
"""

import logging
from typing import Dict, Any
from tools.slack_tool import SlackTool

logger = logging.getLogger(__name__)

class SlackAgent:
    """Agent specialized in handling Slack conversation history queries."""
    
    def __init__(self, slack_tool: SlackTool):
        self.slack_tool = slack_tool
    
    def process_query(self, question: str) -> str:
        """
        Process a query related to Slack conversation history.
        
        Args:
            question: The user's question
            
        Returns:
            Response from Slack search with sources
        """
        try:
            logger.info(f"Processing Slack query: {question[:50]}...")
            
            # Search Slack using the tool
            result = self.slack_tool.get_tool().func(question)
            
            logger.info("Slack query processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing Slack query: {e}")
            return f"Sorry, I encountered an error searching conversation history: {str(e)}"
    
    def add_message(self, user: str, text: str, channel: str, permalink: str):
        """
        Add a new Slack message to the vector store for future searches.
        
        Args:
            user: Username who sent the message
            text: Message content
            channel: Channel where message was sent
            permalink: Slack permalink to the message
        """
        try:
            self.slack_tool.add_message(user, text, channel, permalink)
            logger.debug(f"Added message from {user} to Slack collection")
        except Exception as e:
            logger.error(f"Error adding Slack message: {e}")
            raise
    
    def add_enhanced_message(self, user: str, user_name: str, text: str, channel: str,
                           channel_name: str, message_ts: str, permalink: str):
        """
        Add a new Slack message with enhanced metadata to the vector store.
        
        Args:
            user: User ID who sent the message
            user_name: Display name of the user
            text: Message content
            channel: Channel ID where message was sent
            channel_name: Channel name
            message_ts: Message timestamp
            permalink: Slack permalink to the message
        """
        try:
            self.slack_tool.add_enhanced_message(
                user, user_name, text, channel, channel_name, message_ts, permalink
            )
            logger.debug(f"Added enhanced message from {user_name} in #{channel_name}")
        except Exception as e:
            logger.error(f"Error adding enhanced Slack message: {e}")
            raise
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get status information about the Slack collection.
        
        Returns:
            Dictionary with collection status information
        """
        try:
            count = self.slack_tool.get_collection_count()
            return {
                "collection_name": "Slack Conversations",
                "document_count": count,
                "status": "active" if count > 0 else "empty"
            }
        except Exception as e:
            logger.error(f"Error getting Slack collection status: {e}")
            return {
                "collection_name": "Slack Conversations",
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
            "What did we discuss about the API changes?",
            "Who mentioned the deployment issues?",
            "What was decided in yesterday's standup?",
            "Recent discussions about the bug fix",
            "What did John say about the timeline?",
            "Any updates on the feature release?",
            "What are people saying about the new design?",
            "Recent conversations about performance issues"
        ]
    
    def get_recent_activity_summary(self) -> str:
        """
        Get a summary of recent Slack activity.
        
        Returns:
            Summary string of recent activity
        """
        try:
            count = self.slack_tool.get_collection_count()
            if count == 0:
                return "No Slack messages have been indexed yet."
            
            return f"Currently tracking {count} Slack messages for search and context."
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return "Unable to retrieve activity summary."
    
    def get_related_context(self, query: str, limit: int = 10) -> str:
        """
        Get related conversation context based on the query for better understanding.
        
        Args:
            query: The search query to find related messages
            limit: Number of related messages to include
            
        Returns:
            String with related conversation context
        """
        try:
            return self.slack_tool.get_related_context(query, limit)
        except Exception as e:
            logger.error(f"Error getting related context: {e}")
            return "Unable to retrieve related conversation context."

    def get_recent_context(self, limit: int = 10) -> str:
        """
        Get recent conversation context for better query understanding.
        
        Args:
            limit: Number of recent messages to include
            
        Returns:
            String with recent conversation context
        """
        try:
            return self.slack_tool.get_recent_context(limit)
        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return "Unable to retrieve recent conversation context."