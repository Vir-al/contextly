#!/usr/bin/env python3
"""
Contextly Modular Management Script
Comprehensive management utilities for the modular Contextly system.
"""

import asyncio
import argparse
import logging
import sys
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Core components
from core.config import Config
from core.response_models import SystemStatus

# Tools
from tools.confluence_tool import ConfluenceTool
from tools.slack_tool import SlackTool
from tools.jira_tool import JiraTool

# Agents
from agents.confluence_agent import ConfluenceAgent
from agents.slack_agent import SlackAgent
from agents.jira_agent import JiraAgent

# Loaders
from loaders.confluence_loader import ConfluenceDataLoader

class ContextlyManager:
    """Comprehensive management interface for Contextly system."""
    
    def __init__(self):
        try:
            self.config = Config()
            self._setup_logging()
            self._initialize_components()
            self.logger.info("✅ Contextly Manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Contextly Manager: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Initialize all system components."""
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
        self.jira_tool = JiraTool(self.llm)
        
        # Initialize agents
        self.confluence_agent = ConfluenceAgent(self.confluence_tool)
        self.slack_agent = SlackAgent(self.slack_tool)
        self.jira_agent = JiraAgent(self.jira_tool)
        
        # Initialize loaders
        self.confluence_loader = ConfluenceDataLoader(self.config, self.confluence_tool)
    
    def system_check(self) -> SystemStatus:
        """Perform comprehensive system health check."""
        self.logger.info("🔍 Performing comprehensive system health check...")
        
        errors = []
        integrations = {}
        collections = {}
        
        # Check integrations
        integration_status = self.config.get_integration_status()
        for integration, status in integration_status.items():
            integrations[integration] = {
                "status": "healthy" if status else "disabled",
                "enabled": status
            }
        
        # Test Jira connection if enabled
        if integration_status.get("jira"):
            jira_status = self.jira_agent.test_connection()
            integrations["jira"]["connection"] = jira_status["status"]
            if jira_status["status"] != "connected":
                errors.append(f"Jira connection failed: {jira_status['message']}")
        
        # Check vector store collections
        collections["confluence"] = self.confluence_agent.get_collection_status()
        collections["slack"] = self.slack_agent.get_collection_status()
        
        # Determine overall status
        overall_status = "healthy"
        if errors:
            overall_status = "degraded" if len(errors) < 3 else "error"
        
        status = SystemStatus(
            status=overall_status,
            integrations=integrations,
            collections=collections,
            errors=errors if errors else None
        )
        
        # Log results
        self._log_system_status(status)
        
        return status
    
    def _log_system_status(self, status: SystemStatus):
        """Log system status in a readable format."""
        self.logger.info(f"📊 Overall System Status: {status.status.upper()}")
        
        self.logger.info("🔌 Integrations:")
        for name, info in status.integrations.items():
            emoji = "✅" if info["status"] == "healthy" else "⚠️" if info["status"] == "disabled" else "❌"
            self.logger.info(f"  {emoji} {name.title()}: {info['status']}")
        
        self.logger.info("📚 Collections:")
        for name, info in status.collections.items():
            emoji = "✅" if info["status"] == "active" else "⚠️" if info["status"] == "empty" else "❌"
            count = info.get("document_count", 0)
            self.logger.info(f"  {emoji} {name.title()}: {info['status']} ({count} documents)")
        
        if status.errors:
            self.logger.warning("⚠️  Issues found:")
            for error in status.errors:
                self.logger.warning(f"  • {error}")
    
    def load_confluence_data(self) -> bool:
        """Load Confluence data into vector store."""
        if not self.config.is_confluence_configured():
            self.logger.error("❌ Confluence is not configured")
            return False
        
        return self.confluence_loader.load_confluence_data()
    
    def check_collections(self):
        """Check status of all vector store collections."""
        self.logger.info("📚 Checking vector store collections...")
        
        confluence_status = self.confluence_loader.check_collection_status()
        slack_status = self.slack_agent.get_collection_status()
        
        self.logger.info(f"Confluence Collection:")
        self.logger.info(f"  • Name: {confluence_status['collection_name']}")
        self.logger.info(f"  • Documents: {confluence_status['document_count']}")
        self.logger.info(f"  • Status: {confluence_status['status']}")
        
        if confluence_status.get('spaces_configured'):
            self.logger.info(f"  • Spaces: {confluence_status['space_keys']}")
        
        self.logger.info(f"Slack Collection:")
        self.logger.info(f"  • Name: {slack_status['collection_name']}")
        self.logger.info(f"  • Documents: {slack_status['document_count']}")
        self.logger.info(f"  • Status: {slack_status['status']}")
    
    
    def test_query(self, query: str):
        """Test a query against the system."""
        self.logger.info(f"🧪 Testing query: '{query}'")
        
        # Test with each agent individually
        agents = {
            "confluence": self.confluence_agent,
            "slack": self.slack_agent,
            "jira": self.jira_agent
        }
        
        for agent_name, agent in agents.items():
            try:
                if agent_name == "jira" and not self.jira_tool.is_available():
                    self.logger.info(f"  {agent_name}: Skipped (not configured)")
                    continue
                
                result = agent.process_query(query)
                self.logger.info(f"  {agent_name}: {result[:100]}...")
            except Exception as e:
                self.logger.error(f"  {agent_name}: Error - {e}")
    
    def show_config(self):
        """Display current configuration."""
        config_dict = self.config.to_dict()
        
        self.logger.info("⚙️  Current Configuration:")
        for key, value in config_dict.items():
            if key == "integrations":
                self.logger.info(f"  {key}:")
                for integration, status in value.items():
                    emoji = "✅" if status else "❌"
                    self.logger.info(f"    {emoji} {integration}")
            else:
                self.logger.info(f"  {key}: {value}")

def main():
    parser = argparse.ArgumentParser(description='Contextly Modular Management')
    parser.add_argument('command', choices=[
        'check',
        'load-confluence',
        'check-collections',
        'test-query',
        'show-config'
    ], help='Command to execute')
    
    parser.add_argument('--query', type=str, help='Query to test (for test-query command)')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ContextlyManager()
    
    # Execute command
    if args.command == 'check':
        manager.system_check()
    elif args.command == 'load-confluence':
        success = manager.load_confluence_data()
        sys.exit(0 if success else 1)
    elif args.command == 'check-collections':
        manager.check_collections()
    elif args.command == 'test-query':
        if not args.query:
            print("❌ --query argument required for test-query command")
            sys.exit(1)
        manager.test_query(args.query)
    elif args.command == 'show-config':
        manager.show_config()

if __name__ == '__main__':
    main()