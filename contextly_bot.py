"""
Contextly Bot - Modular Main Application
Multi-agent Slack bot with ChromaDB vector storage.
"""

import asyncio
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from cachetools import TTLCache
# Core components
from client.notion_fetcher import NotionClient
from core.config import Config
from core.workflow_graph import ContextlyWorkflowV2
from core.response_models import ContextlyResponse
from core.mcp_client import ContextlyMCPClient

# Tools
from tools.confluence_tool import ConfluenceTool
from tools.notion_tool import NotionTool
from tools.slack_tool import SlackTool
from tools.jira_tool import JiraTool

# Agents
from agents.contextly_agent import  ContextlyAgent

thread_cache = TTLCache(maxsize=1000, ttl=600)  # Cache threads for 10 minutes
user_cache = TTLCache(maxsize=1000, ttl=3600)   # Cache user info for 1 hour
channel_cache = TTLCache(maxsize=1000, ttl=3600) # Cache channel info for 1 hou

class ContextlyBot:
    """Main Contextly bot application with modular architecture."""
    
    def __init__(self):
        # Load configuration
        self.config = Config()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Slack app
        self.app = AsyncApp(token=self.config.slack_bot_token)
        self.bot_user_id = None
        
        # Initialize AI models
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.llm_model,
            google_api_key=self.config.google_api_key,
            temperature=self.config.llm_temperature
        )
        
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model=self.config.embedding_model,
            google_api_key=self.config.google_api_key
        )
        
        # Initialize tools
        self.confluence_tool = ConfluenceTool(self.llm, self.embedding_model)
        self.slack_tool = SlackTool(self.llm, self.embedding_model)
        self.notion_tool = NotionTool(self.llm, self.embedding_model)
        # Initialize MCP client and agent if configured
        self.contextual_agent = ContextlyAgent(self.llm, self.embedding_model)
        self.workflow = ContextlyWorkflowV2(self.contextual_agent)
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info("🤖 Contextly Bot initialized successfully")

    async def _get_user_name(self, user_id: str, client) -> str:
        """Fetches a user's real name and caches it."""
        if user_id in user_cache:
            return user_cache[user_id]
        try:
            user_info = await client.users_info(user=user_id)
            name = user_info["user"]["real_name"]
            user_cache[user_id] = name
            return name
        except Exception as e:
            self.logger.error(f"Failed to get user name for {user_id}: {e}")
            return "Unknown User"

    async def _get_channel_name(self, channel_id: str, client) -> str:
        """Fetches a channel's name and caches it."""
        if channel_id in channel_cache:
            return channel_cache[channel_id]
        try:
            channel_info = await client.conversations_info(channel=channel_id)
            name = channel_info["channel"]["name"]
            channel_cache[channel_id] = name
            return name
        except Exception as e:
            self.logger.error(f"Failed to get channel name for {channel_id}: {e}")
            return "unknown-channel"
    
    # This new function encapsulates the indexing logic.
    async def _handle_message_indexing(self, event: dict, client, logger):
            """
            Determines if a message is a thread reply or a new message and
            calls the appropriate indexing function from SlackTool.
            """
            user = event.get("user")
            text = event.get("text", "").strip()
            channel = event.get("channel")
            message_ts = event.get("ts")
            thread_ts = event.get("thread_ts")

            # A message is a reply in a thread if thread_ts exists and is different from its own timestamp
            is_threaded_reply = thread_ts and thread_ts != message_ts

            # We don't index DMs to respect privacy
            if channel.startswith("D"):
                return

            if is_threaded_reply:
                # This is a reply, so we process the whole thread for context.
                if thread_ts in thread_cache:
                    logger.info(f"Thread {thread_ts} was recently indexed. Skipping.")
                    return
                
                try:
                    # Fetch all messages from the thread
                    thread_replies = await client.conversations_replies(channel=channel, ts=thread_ts)
                    messages = thread_replies.get("messages", [])
                    
                    if messages:
                        # Get channel name and permalink for the parent message
                        channel_name = await self._get_channel_name(channel, client)
                        permalink_response = await client.chat_getPermalink(channel=channel, message_ts=thread_ts)
                        permalink = permalink_response.get("permalink")

                        # Use the new tool method to add the entire thread
                        self.slack_tool.add_thread_context(
                            thread_messages=messages,
                            channel=channel,
                            channel_name=channel_name,
                            thread_ts=thread_ts,
                            permalink=permalink
                        )
                        # Mark this thread as processed in our cache
                        thread_cache[thread_ts] = True

                except Exception as e:
                    logger.error(f"Failed to process thread {thread_ts}: {e}", exc_info=True)

            else:
                # This is a new parent message, not a reply in a thread
                try:
                    user_name = await self._get_user_name(user, client)
                    channel_name = await self._get_channel_name(channel, client)
                    permalink_response = await client.chat_getPermalink(channel=channel, message_ts=message_ts)
                    permalink = permalink_response.get("permalink")

                    # Use the tool method for single, enhanced messages
                    self.slack_tool.add_enhanced_message(
                        user=user,
                        user_name=user_name,
                        text=text,
                        channel=channel,
                        channel_name=channel_name,
                        message_ts=message_ts,
                        permalink=permalink
                    )
                except Exception as e:
                    logger.error(f"Failed to process single message {message_ts}: {e}", exc_info=True)
    
    def _setup_event_handlers(self):
        """Setup Slack event handlers."""

        @self.app.command("/load_notion")  
        async def handle_load_notion_command(ack, body, client, say, logger):
            """
            Handles the /load_notion slash command to trigger a full re-indexing
            of the Notion workspace.
            """
            # Acknowledge the command immediately to prevent a timeout error
            await ack()

            channel_id = body["channel_id"]
            user_id = body["user_id"]

            try:
                # 1. Post an initial message to the channel
                initial_message = await client.chat_postMessage(
                    channel=channel_id,
                    text=f"🤖 Understood, <@{user_id}>! Starting the Notion workspace indexing process. This may take a few minutes..."
                )
                thread_ts = initial_message["ts"]

                # 2. Begin the actual indexing process, providing updates along the way.
                # We'll pass the client, channel, and thread timestamp to the indexing function
                # so it can post updates directly.
                await self.run_notion_indexing_with_updates(client, channel_id, thread_ts)

                # 3. Post a final success message
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text="✅ Notion workspace has been successfully indexed and is ready for queries."
                )

            except Exception as e:
                logger.error(f"Error during Notion indexing command: {e}", exc_info=True)
                await say(
                    channel=channel_id,
                    text=f"💥 An error occurred during indexing: {e}"
                )
        
        @self.app.event("message")
        async def handle_all_messages(body, say, client, logger):
            """Handle all messages in channels where the bot is present."""
            event = body.get("event", {})
            user = event.get("user")
            text = event.get("text", "").strip()
            channel = event.get("channel")
            message_ts = event.get("ts")
            subtype = event.get("subtype")
            
            # Skip if no text, message from bot itself, or system messages
            if not text or user == self.bot_user_id or subtype in ["bot_message", "channel_join", "channel_leave"]:
                return
            
            # Always index messages for context (except DMs to avoid privacy issues)
            if not channel.startswith("D"):
                await self._index_slack_message(
                    user, text, channel, message_ts, client
                )
        
        @self.app.event("app_mention")
        async def handle_mentions(body, say, client, logger):
            """Handle direct mentions of the bot."""
            event = body.get("event", {})
            user = event.get("user")
            text = event.get("text", "").strip()
            channel = event.get("channel")
            message_ts = event.get("ts")
            thread_ts = event.get("thread_ts") or message_ts
            
            # Skip if no text or message from bot itself
            if not text or user == self.bot_user_id:
                return
            
            await self._handle_bot_query(
                text, user, channel, message_ts, thread_ts, say, client
            )
    
    async def _handle_bot_query(
        self, 
        text: str, 
        user: str, 
        channel: str, 
        message_ts: str,
        thread_ts: str,
        say, 
        client
    ):
        """Handle queries directed to the bot."""
        thinking_message = await say(
            text="Thinking... :thinking_face:", 
            thread_ts=thread_ts
        )
        
        try:
            # Clean the message text
            cleaned_text = text.replace(f"<@{self.bot_user_id}>", "").strip()
            
            # Handle special commands
            if cleaned_text.lower() in ['status', 'help', 'info']:
                await self._handle_status_command(client, channel, thinking_message["ts"])
                return
            
            # Process query through workflow
            response_object = await  self.workflow.invoke(
                cleaned_text,
                thread_ts
            )
            
            # # Add a safety check in case the workflow returns None or an error
            # if not response_object:
            #     raise ValueError("Workflow did not return a valid response object.")

            # # 2. Use your new formatting function to convert the object into Slack blocks.
            # response_blocks = self._format_slack_response(response_object)
            
            # # 3. Use the summary from the object as the fallback text for notifications.
            # fallback_text = response_object.summary

            # 4. Update the "thinking" message with the richly formatted blocks.
            await client.chat_update(
                channel=channel,
                ts=thinking_message["ts"],
                text=response_object      # Fallback text for notifications
                # blocks=response_blocks   # The richly formatted message
            )


            
        except Exception as e:
            self.logger.error(f"Error handling bot query: {e}", exc_info=True)
            await client.chat_update(
                channel=channel,
                ts=thinking_message["ts"],
                text=f"Sorry, I encountered an error: `{str(e)}`"
            )

    async def run_notion_indexing_with_updates(self, client, channel_id: str, thread_ts: str):
        """
        The core logic for indexing Notion, modified to send Slack updates.
        """
        self.logger.debug("Starting Notion workspace indexing with Slack updates...")
        await client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=" Kicking off the process and fetching all pages and databases from Notion..."
        )
        notion_client = NotionClient()
        await self.notion_tool.index_workspace(notion_client)
        
    
    async def _handle_status_command(self, client, channel: str, message_ts: str):
        """Handle status/help commands."""
        try:
            system_status = self.get_system_status()
            slack_status = system_status.get('slack_status', {})
            
            status_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🤖 Contextly Bot Status*\n\nI'm actively listening to messages in this channel and storing them for context when you ask questions!"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Messages Indexed:*\n{slack_status.get('document_count', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{slack_status.get('status', 'unknown').title()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*💡 How to use me:*\n• Just mention me with `@Contextly` followed by your question\n• I'll search through our conversation history to provide relevant context\n• Ask me things like:\n  - \"What did we discuss about the API changes?\"\n  - \"Who mentioned the deployment issues?\"\n  - \"What was decided in yesterday's standup?\""
                    }
                }
            ]
            
            # Add recent context if available
            try:
                recent_context = self.slack_agent.get_recent_context(3)
                if "Recent conversation context:" in recent_context:
                    status_blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*📝 Recent Activity:*\n```{recent_context}```"
                        }
                    })
            except Exception as e:
                self.logger.warning(f"Could not get recent context for status: {e}")
            
            await client.chat_update(
                channel=channel,
                ts=message_ts,
                text="Contextly Bot Status",
                blocks=status_blocks
            )
            
        except Exception as e:
            self.logger.error(f"Error handling status command: {e}")
            await client.chat_update(
                channel=channel,
                ts=message_ts,
                text=f"Sorry, I encountered an error getting status: `{str(e)}`"
            )
    
    async def _index_slack_message(
        self,
        user: str,
        text: str,
        channel: str,
        message_ts: str,
        client
    ):
        """Index a Slack message for future search with enhanced metadata."""
        try:
            # Skip indexing messages that mention "contextly" (case-insensitive)
            if "contextly" in text.lower():
                self.logger.debug(f"Skipping indexing message mentioning 'contextly': {text[:50]}...")
                return
            
            # Get permalink for the message
            permalink_response = await client.chat_getPermalink(
                channel=channel,
                message_ts=message_ts
            )
            permalink = permalink_response.get('permalink')
            
            # Get channel info for better context
            channel_info = await client.conversations_info(channel=channel)
            channel_name = channel_info.get('channel', {}).get('name', 'unknown')
            
            # Get user info for better context
            user_info = await client.users_info(user=user)
            user_name = user_info.get('user', {}).get('real_name') or user_info.get('user', {}).get('name', 'unknown')
            
            # Add enhanced message to Slack agent for indexing
            self.slack_tool.add_enhanced_message(
                user=user,
                user_name=user_name,
                text=text,
                channel=channel,
                channel_name=channel_name,
                message_ts=message_ts,
                permalink=permalink
            )
            
            self.logger.debug(f"Indexed message from {user_name} in #{channel_name}")
            
        except Exception as e:
            self.logger.error(f"Error indexing Slack message: {e}")
    
    def _format_slack_response(self, response: ContextlyResponse) -> list:
        """
        Formats the structured ContextlyResponse into a rich Slack Block Kit message.
        """
        # 1. Start with the main summary block. This is always present.
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": response.summary or "I found some information but couldn't generate a summary."
                }
            }
        ]

        # 2. Build a list of all footer elements (references, next steps, etc.)
        footer_elements = []

        # Add references if available
        if response.references:
            # Create a clean list of formatted markdown links, filtering out any empty ones
            ref_links = [f"• <{ref}|Source>" for ref in response.references if ref]
            if ref_links:
                # The join adds a newline between each bullet point
                footer_elements.append({
                    "type": "mrkdwn",
                    "text": f"*🔗 References:*\n" + "\n".join(ref_links)
                })

        # Add next steps if available
        if response.next_steps:
            footer_elements.append({
                "type": "mrkdwn",
                "text": f"*➡️ Next Steps:*\n_{response.next_steps}_"
            })

        # Add agent info if available (with the formatting fix)
        if response.tool_used:
            # **THE FIX:** Correctly join the list of tools into a comma-separated string
            tools_text = ", ".join(response.tool_used)
            footer_elements.append({
                "type": "mrkdwn",
                # Use backticks ` for a nice code-like style for tool names
                "text": f"⚙️ Processed by: `{tools_text}`"
            })

        # 3. If we have any footer elements, add a divider and the context block
        if footer_elements:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "context",
                "elements": footer_elements
            })

        return blocks

    async def start(self):
        """Start the Contextly bot."""
        try:
            # Get bot user ID
            auth_response = await self.app.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            
            
            # Start socket mode handler
            handler = AsyncSocketModeHandler(self.app, self.config.slack_app_token)
            
            self.logger.info("🚀 Starting Contextly Bot with modular architecture...")
            self.logger.info(f"📊 Configuration: {self.config.get_integration_status()}")
            
            await handler.start_async()
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}", exc_info=True)
            raise
    

async def main():
    """Main entry point."""
    bot = ContextlyBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())