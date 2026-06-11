"""
Configuration Management
Centralized configuration for the Contextly system.
"""

import os
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Centralized configuration management for Contextly."""
    
    def __init__(self):
        load_dotenv()
        self._validate_required_config()
    
    # Slack Configuration
    @property
    def slack_app_token(self) -> str:
        return os.environ["SLACK_APP_TOKEN"]
    
    @property
    def slack_bot_token(self) -> str:
        return os.environ["SLACK_BOT_TOKEN"]
    
    # LLM Provider Configuration
    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "aws_bedrock")  # "google" or "aws_bedrock"
    
    # Google AI Configuration
    @property
    def google_api_key(self) -> str:
        return os.environ.get("GOOGLE_API_KEY", "")
    
    # AWS Bedrock Configuration
    @property
    def aws_profile(self) -> str:
        return os.getenv("AWS_PROFILE", "default")
    
    @property
    def aws_region(self) -> str:
        return os.getenv("AWS_REGION", "us-east-1")
    
    @property
    def aws_bedrock_model(self) -> str:
        return os.getenv("AWS_BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
    
    @property
    def llm_model(self) -> str:
        if self.llm_provider == "aws_bedrock":
            return self.aws_bedrock_model
        return os.getenv("LLM_MODEL", "gemini-2.0-flash-001")
    
    @property
    def embedding_model(self) -> str:
        return os.getenv("EMBEDDING_MODEL", "models/embedding-001")
    
    @property
    def llm_temperature(self) -> float:
        return float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # ChromaDB Configuration
    @property
    def chroma_persist_directory(self) -> str:
        return os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    
    @property
    def confluence_collection(self) -> str:
        return os.getenv("CONFLUENCE_COLLECTION", "contextly_confluence")
    
    @property
    def slack_collection(self) -> str:
        return os.getenv("SLACK_COLLECTION", "contextly_slack")
    
    # Confluence Configuration (Optional)
    @property
    def confluence_url(self) -> Optional[str]:
        return os.getenv("CONFLUENCE_URL")
    
    @property
    def confluence_username(self) -> Optional[str]:
        return os.getenv("CONFLUENCE_USERNAME")
    
    @property
    def confluence_api_token(self) -> Optional[str]:
        return os.getenv("CONFLUENCE_API_TOKEN")
    
    @property
    def confluence_space_keys(self) -> list:
        space_keys = os.getenv("CONFLUENCE_SPACE_KEYS", "")
        return [key.strip() for key in space_keys.split(',') if key.strip()]
    
    # Jira Configuration (Optional)
    @property
    def jira_instance_url(self) -> Optional[str]:
        return os.getenv("JIRA_INSTANCE_URL")
    
    @property
    def jira_email(self) -> Optional[str]:
        return os.getenv("JIRA_EMAIL")
    
    @property
    def jira_api_token(self) -> Optional[str]:
        return os.getenv("JIRA_API_TOKEN")
    
    @property
    def notion_integration_token(self) -> Optional[str]:
        return os.getenv("NOTION_INTEGRATION_TOKEN")

    @property
    def jira_cloud(self) -> str:
        return os.getenv("JIRA_CLOUD", "true")
    
    # MCP Configuration
    @property
    def mcp_servers_config(self) -> dict:
        """Get MCP servers configuration from environment variables."""
        config = {
             "atlassian": {
             "url": "https://mcp.atlassian.com/v1/sse",
             "transport": "sse",
             "command": "mcp-atlassian",
             "args": [
             "--jira-url", "https://bazaarvoice.atlassian.net",
             "--jira-username", self.jira_email,
             "--jira-token", self.jira_api_token,
             "--confluence-url", "https://bazaarvoice.atlassian.net/wiki",
             "--confluence-username", self.confluence_username,
             "--confluence-token", self.confluence_api_token
        ],
      "env": {},
      "disabled": False
       }
   }
        return config
    
    @property
    def mcp_enabled(self) -> bool:
        """Check if MCP integration is enabled."""
        return len(self.mcp_servers_config) > 0
    
    # System Configuration
    
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")
    
    def _validate_required_config(self) -> None:
        """Validate that all required configuration is present."""
        required_vars = [
            "SLACK_APP_TOKEN",
            "SLACK_BOT_TOKEN"
        ]
        
        # Check LLM provider specific requirements
        llm_provider = self.llm_provider
        if llm_provider == "google":
            if not os.getenv("GOOGLE_API_KEY"):
                required_vars.append("GOOGLE_API_KEY")
        elif llm_provider == "aws_bedrock":
            # AWS credentials are handled by boto3/AWS CLI, so we just need the profile
            pass
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please check your .env file."
            )
    
    def is_confluence_configured(self) -> bool:
        """Check if Confluence integration is properly configured."""
        return all([
            self.confluence_url,
            self.confluence_username,
            self.confluence_api_token,
            self.confluence_space_keys
        ])
    
    def is_jira_configured(self) -> bool:
        """Check if Jira integration is properly configured."""
        return all([
            self.jira_instance_url,
            self.jira_email,
            self.jira_api_token
        ])
    
    def get_integration_status(self) -> dict:
        """Get status of all integrations."""
        return {
            "slack": True,  # Always true if we get this far
            "google_ai": True,  # Always true if we get this far
            "confluence": self.is_confluence_configured(),
            "jira": self.is_jira_configured(),
            "mcp": self.mcp_enabled,
            "chromadb": True  # ChromaDB is always available
        }
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "llm_temperature": self.llm_temperature,
            "chroma_persist_directory": self.chroma_persist_directory,
            "confluence_collection": self.confluence_collection,
            "slack_collection": self.slack_collection,
            "log_level": self.log_level,
            "integrations": self.get_integration_status()
        }