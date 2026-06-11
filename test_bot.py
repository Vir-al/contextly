#!/usr/bin/env python3
"""
Test script for Contextly Bot
Tests the message listening and context storage functionality.
"""

import asyncio
import logging
from contextly_bot import ContextlyBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_bot_initialization():
    """Test bot initialization and status."""
    print("🧪 Testing Contextly Bot initialization...")
    
    try:
        bot = ContextlyBot()
        print("✅ Bot initialized successfully")
        
        # Test system status
        status = bot.get_system_status()
        print(f"📊 System Status: {status}")
        
        # Test Slack agent functionality
        slack_status = bot.slack_agent.get_collection_status()
        print(f"💬 Slack Status: {slack_status}")
        
        # Test recent context (should be empty initially)
        recent_context = bot.slack_agent.get_recent_context(5)
        print(f"📝 Recent Context: {recent_context}")
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

async def main():
    """Main test function."""
    await test_bot_initialization()
    print("\n🎉 Bot is ready to listen to Slack messages and store them for context!")
    print("\nTo use the bot:")
    print("1. Make sure your .env file has the required Slack tokens")
    print("2. Run: python contextly_bot.py")
    print("3. The bot will listen to all messages in channels where it's added")
    print("4. Mention @Contextly with questions to get contextual responses")
    print("5. Use '@Contextly status' to see how many messages are indexed")

if __name__ == "__main__":
    asyncio.run(main())