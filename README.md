# Contextly - Modular Multi-Agent Slack Bot

Contextly is a sophisticated, modular Slack bot that provides intelligent responses using specialized agents for Confluence documentation, Slack conversations, Jira tickets, and MCP (Model Context Protocol) servers. Built with ChromaDB for local vector storage - no Docker required!

## 🏗️ Modular Architecture

```
contextly/
├── core/                    # Core system components
│   ├── config.py           # Configuration management
│   ├── response_models.py  # Data models
│   ├── workflow.py         # LangGraph orchestration
│   └── mcp_client.py       # MCP client integration
├── tools/                   # Specialized tools
│   ├── confluence_tool.py  # Confluence search
│   ├── slack_tool.py       # Slack processing
│   └── jira_tool.py        # Jira operations
├── agents/                  # Intelligent agents
│   ├── router_agent.py     # Query routing
│   ├── confluence_agent.py # Documentation queries
│   ├── slack_agent.py      # Conversation queries
│   ├── jira_agent.py       # Project management
│   ├── mcp_agent.py        # MCP server integration
│   └── profile_agent.py    # User profiles
├── loaders/                 # Data processing
│   └── confluence_loader.py # Confluence data loading
├── examples/                # Example MCP servers
│   └── math_server.py      # Sample math MCP server
├── contextly_bot.py         # Main application
├── manage_modular.py        # Management interface
└── run_modular.sh          # Quick start script
```

## 🚀 Quick Start (No Docker Required!)

### 1. Setup Environment

```bash
# Clone and enter directory
cd contextly

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy configuration template
cp .env.example .env

# Edit with your credentials
nano .env  # or your preferred editor
```

Required environment variables:

```env
SLACK_APP_TOKEN=xapp-your-token
SLACK_BOT_TOKEN=xoxb-your-token
GOOGLE_API_KEY=your-google-ai-key
```

### 3. Run

```bash
# Quick start (recommended)
./run_modular.sh

# Or manual start
python contextly_bot.py
```

## ⚙️ Management Commands

```bash
# System health check
python manage_modular.py check

# Load Confluence documentation
python manage_modular.py load-confluence

# Check vector store collections
python manage_modular.py check-collections

# Test a query
python manage_modular.py test-query --query "How do I deploy?"

# Show system configuration
python manage_modular.py show-config

# View user profiles
python manage_modular.py show-profiles

# Clear user profiles
python manage_modular.py clear-profiles
```

## 🔧 Configuration

### Required Settings

- **SLACK_APP_TOKEN**: Your Slack app token (starts with `xapp-`)
- **SLACK_BOT_TOKEN**: Your Slack bot token (starts with `xoxb-`)
- **GOOGLE_API_KEY**: Google AI API key for embeddings and LLM

### Optional Integrations

#### Confluence (for documentation search)

```env
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-token
CONFLUENCE_SPACE_KEYS=SPACE1,SPACE2,SPACE3
```

#### Jira (for ticket management)

```env
JIRA_INSTANCE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token
```

#### MCP Servers (for external tools and APIs)

```env
# Math server (local stdio server)
MCP_MATH_SERVER_PATH=/path/to/your/math_server.py

# Weather server (HTTP server)
MCP_WEATHER_ENABLED=true
MCP_WEATHER_SERVER_URL=http://localhost:8000/mcp/

# Custom MCP servers (JSON format)
MCP_CUSTOM_SERVERS={"custom_server": {"command": "python", "args": ["/path/to/server.py"], "transport": "stdio"}}
```

### ChromaDB Settings

```env
CHROMA_PERSIST_DIRECTORY=./chroma_db
CONFLUENCE_COLLECTION=contextly_confluence
SLACK_COLLECTION=contextly_slack
```

## 🤖 Usage

### Basic Queries

```
@Contextly How do I deploy the application?
@Contextly What did we discuss about the API changes?
@Contextly Create a ticket for the bug fix
@Contextly What's (3 + 5) x 12?
@Contextly What's the weather in NYC?
```

### Profile Management

```
@Contextly set my project to PROJ-123
```

### Query Routing

The bot intelligently routes queries:

- **Documentation** → Confluence Agent

  - "How do I...", "What is the process...", "Show guidelines..."

- **Conversations** → Slack Agent

  - "What did we say about...", "Recent discussion...", "Who mentioned..."

- **Tickets** → Jira Agent

  - "Create a ticket...", "Show my tickets...", "Update status..."

- **External Tools** → MCP Agent
  - "Calculate...", "What's the weather...", "Convert currency..."

## 🏗️ Architecture Details

### Multi-Agent System

- **Router Agent**: Analyzes queries and routes to appropriate agents
- **Confluence Agent**: Searches official documentation
- **Slack Agent**: Queries conversation history
- **Jira Agent**: Manages tickets and projects
- **MCP Agent**: Integrates with external MCP servers for specialized tools
- **Profile Agent**: Handles user settings

### Vector Storage

- **ChromaDB**: Local vector database (no external dependencies)
- **Separate Collections**: Isolated storage for different data types
- **Real-time Indexing**: Automatic Slack message processing

### LangGraph Workflow

- **State Management**: Persistent conversation context
- **Conditional Routing**: Dynamic agent selection
- **Error Handling**: Graceful failure recovery

## 🔍 System Health

### Health Check

```bash
python manage_modular.py check
```

This checks:

- ✅ Environment variables
- ✅ AI model connectivity
- ✅ Vector store collections
- ✅ Integration status
- ✅ Jira connectivity (if configured)

### Collection Status

```bash
python manage_modular.py check-collections
```

Shows document counts and status for:

- Confluence documentation
- Slack conversation history

## 🛠️ Development

### Adding New Tools

1. Create tool in `tools/` directory
2. Implement required methods
3. Add to agent in `agents/`
4. Update workflow routing

### Testing

```bash
# Test individual queries
python manage_modular.py test-query --query "your test query"

# Test system health
python manage_modular.py check
```

### Debugging

- Logs are output to console
- Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging
- Each component has isolated error handling

## 📊 Features

### ✅ What's Included

- Multi-agent query routing
- ChromaDB vector storage (local)
- Real-time Slack message indexing
- User profile management
- Confluence documentation search
- Jira ticket operations
- MCP (Model Context Protocol) server integration
- Comprehensive health checking
- Modular, testable architecture

### 🔄 Data Flow

1. User sends Slack message
2. Router analyzes query intent
3. Appropriate agent processes request
4. Vector store provides context
5. LLM generates response
6. Structured response sent to Slack

## 🔌 MCP (Model Context Protocol) Integration

Contextly supports MCP servers to extend functionality with external tools and APIs.

### What is MCP?

MCP (Model Context Protocol) allows AI assistants to securely connect to external data sources and tools. Contextly can integrate with:

- **Math servers** for calculations
- **Weather APIs** for weather data
- **Custom tools** for specialized operations
- **External databases** for data queries

### Setting Up MCP Servers

#### 1. Math Server (Example)

```bash
# Set the path to your math server
export MCP_MATH_SERVER_PATH=/path/to/contextly/examples/math_server.py
```

The included example math server supports:

- Basic calculations: `(3 + 5) x 12`
- Addition: `add 10 and 20`
- Multiplication: `multiply 7 by 8`

#### 2. Weather Server (HTTP)

```bash
# Enable weather server
export MCP_WEATHER_ENABLED=true
export MCP_WEATHER_SERVER_URL=http://localhost:8000/mcp/
```

#### 3. Custom MCP Servers

```bash
# JSON configuration for multiple servers
export MCP_CUSTOM_SERVERS='{"my_server": {"command": "python", "args": ["/path/to/my_server.py"], "transport": "stdio"}}'
```

### Using MCP Tools

Once configured, you can use MCP tools through natural language:

```
@Contextly What's 15 * 24 + 100?
@Contextly Calculate the square root of 144
@Contextly What's the weather in San Francisco?
```

### Creating Custom MCP Servers

1. **Create your server script** (see `examples/math_server.py`)
2. **Implement required methods**:
   - `tools/list` - List available tools
   - `tools/call` - Execute tool calls
3. **Add to configuration**:
   ```bash
   export MCP_CUSTOM_SERVERS='{"my_tool": {"command": "python", "args": ["/path/to/my_server.py"], "transport": "stdio"}}'
   ```

### MCP Server Types

- **stdio**: Local servers using standard input/output
- **streamable_http**: HTTP servers with streaming support

### Testing MCP Integration

```bash
# Check MCP status
python manage_modular.py check

# Test MCP query
python manage_modular.py test-query --query "What's 5 + 3?"
```

## � Troubleshooting

### Common Issues

**Bot not responding:**

- Check Slack app permissions
- Verify tokens in `.env`
- Run health check: `python manage_modular.py check`

**ChromaDB errors:**

- Ensure `./chroma_db/` directory exists
- Check disk space
- Verify Python version (3.9+)

**No search results:**

- Load data: `python manage_modular.py load-confluence`
- Check collections: `python manage_modular.py check-collections`

### Getting Help

1. Run system check: `python manage_modular.py check`
2. Check logs for error details
3. Verify all environment variables are set
4. Test individual components

## 📄 License

MIT License - see LICENSE file for details.

---

**Ready to get started?** Run `./run_modular.sh` and your Contextly bot will be up and running! 🚀
