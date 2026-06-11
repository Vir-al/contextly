from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.llm_factory import LLMFactory
import os
from dotenv import load_dotenv

# Import the simple agent
from core.config import Config
from agents.simple_support_agent import SimpleCreatorSupportAgent
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

app = FastAPI(title="Simple Creator Marketing Support API", version="1.0.0")

class SimpleQuery(BaseModel):
    query: str
    user_id: str = "anonymous"

class SimpleResponse(BaseModel):
    response: str

# Initialize the simple agent
config = Config()

llm_factory = LLMFactory(config)
llm = llm_factory.create_llm()
embeddings = llm_factory.create_embedding_model()

# Log provider information
provider_info = llm_factory.get_provider_info()
print(f"🚀 Starting server with LLM Provider: {provider_info['provider']}")
print(f"📋 Model: {provider_info['model']}")
# Create the simple support agent
support_agent = SimpleCreatorSupportAgent(llm, embeddings)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Simple Creator Marketing Support API is running", "status": "healthy"}

@app.post("/support/query", response_model=SimpleResponse)
async def support_query(query_data: SimpleQuery):
    """
    Process a support query using the simple AI agent
    
    - **query**: The user's question or support request
    - **user_id**: Optional user identifier for tracking
    """
    if not query_data.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Process the query using the simple agent
        response_text = await support_agent.process_message(query_data.query)
        
        return SimpleResponse(response=response_text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Check the health of the support system"""
    return {
        "status": "healthy",
        "agent": "SimpleCreatorSupportAgent",
        "message": "Simple creator marketing support system is running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)