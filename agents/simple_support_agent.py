"""
Simple Creator Marketing Support Agent

A basic React agent with just RAG functionality for creator marketing support.
"""

import logging
from typing import List
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from datetime import datetime

from core.config import Config
from loaders.creator_marketing_loader import CreatorMarketingDataLoader

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleCreatorSupportAgent:
    """
    Simple React agent for creator marketing support with basic RAG functionality.
    """
    
    def __init__(self, llm: ChatGoogleGenerativeAI, embedding_model: GoogleGenerativeAIEmbeddings):
        """Initialize the simple support agent."""
        
        self.llm = llm
        self.embedding_model = embedding_model
        
        # Initialize the data loader
        self.config = Config()
        self.data_loader = CreatorMarketingDataLoader(self.config)
        self.data_loader.initialize_vectorstore()
        
        # Create the agent
        self.agent_executor = self._create_agent()
        
        logger.info("🚀 Simple Creator Support Agent initialized")
    
    def _create_agent(self) -> AgentExecutor:
        """Create a simple React agent."""
        
        # Simple system prompt with required variables and React format
        system_prompt = """
        You are a helpful Creator Marketing Support Agent. You help content creators with:
        - Affiliate marketing strategies
        - Social media monetization
        - Brand partnerships
        - Email marketing
        - Analytics and performance tracking
        
        Use your knowledge base to provide helpful, actionable advice.
        
        You have access to the following tools:

        {tools}

        Use the following format:

        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question

        Begin!

        Question: {input}
        Thought: {agent_scratchpad}
        """
        
        # Create the agent prompt - use a single template for React format
        agent_prompt = ChatPromptTemplate.from_template(system_prompt)
        
        # Create the React agent
        agent = create_react_agent(
            self.llm,
            self._get_tools(),
            agent_prompt
        )
        
        # Create agent executor
        return AgentExecutor(
            agent=agent,
            tools=self._get_tools(),
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
    
    def _get_tools(self) -> List[Tool]:
        """Get the simple tools for the agent."""
        return [
            self._create_search_tool()
        ]
    
    def _create_search_tool(self) -> Tool:
        """Create a simple search tool for the knowledge base."""
        
        def search_knowledge(query: str) -> str:
            """Search the creator marketing knowledge base."""
            try:
                logger.info(f"🔍 Searching for: {query}")
                
                # Search the knowledge base
                results = self.data_loader.search_documents(query, k=3)
                
                if not results:
                    return "No relevant information found."
                
                # Format results simply
                response = f"Found {len(results)} relevant results:\n\n"
                
                for i, result in enumerate(results, 1):
                    content = result['content']
                    if len(content) > 300:
                        content = content[:300] + "..."
                    
                    response += f"{i}. {content}\n\n"
                
                return response
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                return f"Search error: {str(e)}"
        
        return Tool(
            name="search_creator_knowledge",
            func=search_knowledge,
            description="Search the creator marketing knowledge base for information about affiliate marketing, monetization, social media, brand partnerships, and analytics."
        )
    
    async def process_message(self, message: str) -> str:
        """Process a user message."""
        try:
            logger.info(f"🤖 Processing: {message}")
            
            # Run the agent
            result = self.agent_executor.invoke({
                "input": message
            })
            
            return result["output"]
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def load_knowledge_base(self) -> bool:
        """Load the knowledge base."""
        try:
            return self.data_loader.load_creator_marketing_data()
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return False