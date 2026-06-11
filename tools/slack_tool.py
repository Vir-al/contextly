"""
Slack Tool
Handles searching and retrieving information from Slack conversation history,
with special logic for individual messages and full conversation threads.
"""

import os
import logging
from typing import Dict, Any, List
from langchain.agents import Tool
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate

# Assuming you have a Slack client instance available to pass in
# from slack_sdk.web.async_client import AsyncWebClient
# For type hinting, you can use the following if your client is available
# from slack_bolt.async_app import AsyncApp

logger = logging.getLogger(__name__)

class SlackTool:
    """Tool for searching Slack conversation history using a ChromaDB vector store."""
    
    def __init__(self, llm: ChatGoogleGenerativeAI, embedding_model: GoogleGenerativeAIEmbeddings):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vectorstore = self._initialize_vectorstore()
        self.tool = self._create_tool()
    
    def _initialize_vectorstore(self) -> Chroma:
        """Initialize the Slack ChromaDB vector store from a persistent directory."""
        chroma_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        collection_name = os.getenv("SLACK_COLLECTION", "contextly_slack")
        
        # Creates a dedicated subdirectory for the Slack vector data
        persist_directory = os.path.join(chroma_dir, "slack")
        logger.info(f"Initializing ChromaDB for Slack at: {persist_directory}")
        
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=persist_directory
        )
    
    def _format_results_with_sources(self, result: Dict[str, Any]) -> str:
        """Format QA results with source attribution."""
        answer = result.get('result', "No answer found.")
        source_docs = result.get('source_documents', [])
        # Use a set to avoid duplicate URLs if multiple chunks come from the same source
        references = {doc.metadata.get('source_url', 'Source not available') for doc in source_docs}
        
        if references:
            sources_text = "\n".join([f"- {ref}" for ref in references])
            return f"Answer: {answer}\n\nSources:\n{sources_text}"
        return f"Answer: {answer}"
    
    def _search_slack(self, query: str) -> str:
        """Search Slack conversation history with enhanced context."""
        try:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
            
            template = """You are analyzing Slack conversation history to answer a question. The history may include single messages or entire conversation threads.

Use the following pieces of conversation history to answer the question at the end. Focus on:
- Who said what and when.
- The context of the entire thread if the history is from a thread.
- What decisions were made.
- Any action items or next steps mentioned.
- The channel context (which team/topic the discussion was about).

If you don't have enough information from the conversations to answer, just say that.

Conversation History:
{context}

Question: {question}

Answer with specific details from the conversations, including who said what and in which channel when relevant:"""

            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=retriever,
                chain_type="stuff",
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": PromptTemplate(
                        template=template,
                        input_variables=["context", "question"]
                    )
                }
            )
            result = qa_chain.invoke(query)
            return self._format_results_with_sources(result)
        except Exception as e:
            logger.error(f"Error searching Slack: {e}", exc_info=True)
            return f"An error occurred while searching Slack history: {str(e)}"
    
    def _create_tool(self) -> Tool:
        """Create the Slack search tool."""
        return Tool(
            name="SearchSlackHistory",
            func=self._search_slack,
            description=(
                "Use for questions about informal team conversations, recent discussions, "
                "ad-hoc decisions, and real-time operational chatter from Slack."
            )
        )
    
    def get_tool(self) -> Tool:
        """Get the Slack tool instance."""
        return self.tool
    
    def add_enhanced_message(self, user: str, user_name: str, text: str, channel: str,
                           channel_name: str, message_ts: str, permalink: str):
        """Add a single, non-threaded Slack message with enhanced metadata to the vector store."""
        try:
            page_content = f"Message from {user_name} in #{channel_name}: {text}"
            
            doc = Document(
                page_content=page_content,
                metadata={
                    "user_id": user,
                    "user_name": user_name,
                    "channel_id": channel,
                    "channel_name": channel_name,
                    "message_ts": message_ts,
                    "source": "slack",
                    "source_url": permalink,
                    "type": "message"
                }
            )
            self.vectorstore.add_documents([doc])
            self.vectorstore.persist()
            logger.debug(f"Added enhanced Slack message from {user_name} in #{channel_name}")
        except Exception as e:
            logger.error(f"Error adding enhanced Slack message: {e}", exc_info=True)
            raise
    
    def add_thread_context(self, thread_messages: List[Dict[str, Any]], channel: str, 
                         channel_name: str, thread_ts: str, permalink: str):
        """
        Adds an entire Slack thread as a single document for rich context.

        Args:
            thread_messages: A list of message objects from client.conversations_replies.
            channel: The ID of the channel where the thread occurred.
            channel_name: The name of the channel.
            thread_ts: The timestamp of the parent message that started the thread.
            permalink: The permalink to the parent message.
        """
        if not thread_messages:
            return
            
        try:
            # Combine all messages into a single, structured text block
            full_thread_text = f"Start of conversation thread in #{channel_name}:\n\n"
            participants = set()
            
            for msg in thread_messages:
                user_name = msg.get('user_profile', {}).get('real_name', msg.get('user', 'Unknown User'))
                text = msg.get('text', '')
                participants.add(user_name)
                full_thread_text += f"---\n{user_name}: {text}\n"

            # Create a single document for the entire thread
            doc = Document(
                page_content=full_thread_text,
                metadata={
                    "channel_id": channel,
                    "channel_name": channel_name,
                    "thread_ts": thread_ts,
                    "source": "slack_thread",
                    "source_url": permalink,
                    "type": "thread",
                    "participants": list(participants),
                    "message_count": len(thread_messages)
                }
            )

            self.vectorstore.add_documents([doc])
            self.vectorstore.persist() # Save changes to disk
            logger.info(f"Successfully indexed full thread context from channel #{channel_name} (ts: {thread_ts}).")

        except Exception as e:
            logger.error(f"Error adding Slack thread context for ts {thread_ts}: {e}", exc_info=True)
            raise
    
    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}", exc_info=True)
            return 0