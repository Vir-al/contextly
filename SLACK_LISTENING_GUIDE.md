# Slack Message Listening & Context Storage

## Overview

The Contextly bot has been enhanced to automatically listen to all messages in Slack channels where it's present and store them for future context when answering questions.

## How It Works

### 1. Message Listening
- The bot listens to **all messages** in channels where it's added (not just mentions)
- Messages are automatically indexed in real-time as they're posted
- Direct messages are handled separately for privacy

### 2. Context Storage
- Each message is stored with rich metadata:
  - User name and ID
  - Channel name and ID
  - Message timestamp
  - Permalink to original message
- Messages are stored in ChromaDB vector database for semantic search

### 3. Context Retrieval
- When you ask the bot a question, it searches through stored conversations
- Uses semantic similarity to find relevant past discussions
- Provides context-aware responses with source links

## Usage

### Basic Usage
```
@Contextly What did we discuss about the API changes?
@Contextly Who mentioned the deployment issues yesterday?
@Contextly What was decided in the standup meeting?
```

### Status Commands
```
@Contextly status    # Shows how many messages are indexed
@Contextly help      # Shows usage information
@Contextly info      # Same as status
```

## Features

### Enhanced Message Indexing
- **Rich Context**: Messages include channel and user context
- **Semantic Search**: Find messages by meaning, not just keywords
- **Source Attribution**: All responses include links back to original messages

### Privacy & Security
- **Channel-Only**: Only indexes public channel messages (not DMs)
- **Bot Messages Excluded**: Ignores messages from bots and system messages
- **Self-Exclusion**: Bot doesn't index its own messages

### Smart Context Usage
- **Recent Context**: Bot considers recent conversations when answering
- **Cross-Channel**: Can find relevant discussions across different channels
- **Time-Aware**: Understands temporal context of discussions

## Technical Details

### Event Handling
The bot listens to two types of Slack events:
- `message` events: For indexing all channel messages
- `app_mention` events: For handling direct queries to the bot

### Storage Structure
Messages are stored with this metadata:
```json
{
  "user_id": "U1234567",
  "user_name": "John Doe",
  "channel_id": "C1234567",
  "channel_name": "general",
  "message_ts": "1234567890.123456",
  "source": "slack",
  "source_url": "https://workspace.slack.com/archives/...",
  "type": "message"
}
```

### Search Enhancement
- Uses custom prompts optimized for conversation history
- Retrieves top 5 most relevant messages for each query
- Formats responses with specific details about who said what and when

## Setup Requirements

### Slack App Permissions
Your Slack app needs these OAuth scopes:
- `channels:history` - Read message history in public channels
- `groups:history` - Read message history in private channels (if needed)
- `chat:write` - Send messages as the bot
- `users:read` - Get user information for context

### Environment Variables
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
GOOGLE_API_KEY=your-google-api-key
```

## Monitoring & Debugging

### Check Status
Use `@Contextly status` to see:
- Number of messages indexed
- Recent conversation activity
- System health

### Logs
The bot logs message indexing activity:
```
DEBUG - Added enhanced message from John Doe in #general
INFO - Indexed message from user123
```

## Best Practices

### For Users
1. **Be Specific**: Ask specific questions about past discussions
2. **Use Context**: Reference timeframes, people, or topics
3. **Check Status**: Use status command to see if messages are being indexed

### For Administrators
1. **Monitor Storage**: Check ChromaDB size regularly
2. **Review Permissions**: Ensure bot has necessary Slack permissions
3. **Test Regularly**: Use test script to verify functionality

## Troubleshooting

### Common Issues

**Bot not indexing messages:**
- Check Slack app permissions
- Verify bot is added to the channel
- Check logs for errors

**No context in responses:**
- Ensure messages have been indexed (check status)
- Try more specific queries
- Check if ChromaDB is accessible

**Missing recent context:**
- Bot needs time to index messages after being added
- Recent context builds up over time
- Check if bot has been restarted recently

### Testing
Run the test script to verify functionality:
```bash
python test_bot.py
```

This will test bot initialization and basic functionality without starting the full Slack connection.