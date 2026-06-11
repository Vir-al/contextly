from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from a .env file.
# This is crucial for securely loading your Slack bot and app tokens.
load_dotenv()

# Initialize the AsyncApp with your bot's token.
# The token allows your bot to authenticate with the Slack API.
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# --- Event Listeners ---

# This event listener handles all types of messages in various conversation types.
# It listens for:
# - message.channels: Messages in public and private channels.
# - message.groups: Messages in private channels (groups).
# - message.im: Messages in direct messages (IMs) with the bot.
# - message.mpim: Messages in multi-person direct messages.
@app.event([
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim"
])
async def handle_all_messages(body, say):
    """
    Handles general messages received by the bot.
    The 'body' contains the full event payload from Slack.
    The 'say' function is used to send a message back to the conversation.
    """
    print("📥 Received general message:", body)
    # Respond to the message. You can add logic here to filter or process messages
    # based on content, sender, etc.
    await say("Echo from test bot!")

# This specific event listener triggers only when the bot is mentioned
# (e.g., @your_bot_name in a channel).
@app.event("app_mention")
async def handle_app_mention(body, say):
    """
    Handles messages where the bot is explicitly mentioned.
    This allows for specific responses when the bot is directly addressed.
    """
    print("📥 Received app mention:", body)
    # Respond to the mention. You might want a different, more direct response here.
    await say("Echo from test bot!")

# --- Main Application Logic ---

async def main():
    """
    The main function to start the Slack bot in Socket Mode.
    Socket Mode allows your bot to connect to Slack over a WebSocket,
    which is useful for local development or environments without public URLs.
    """
    # Initialize the SocketModeHandler with your app instance and app-level token.
    # The app-level token is different from the bot token and starts with 'xapp-'.
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    # Start the Socket Mode handler asynchronously.
    await handler.start_async()

# This block ensures that the main() function is called when the script is executed.
if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
