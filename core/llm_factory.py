"""
LLM Factory
Factory class for creating LLM instances based on configuration.
"""

import os
import logging
from typing import Union, Optional
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from core.config import Config
from core.ssl_config import SSLConfig

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory class for creating LLM and embedding model instances."""
    
    def __init__(self, config: Config):
        """Initialize the LLM factory with configuration."""
        self.config = config
    
    def create_llm(self) -> Union[ChatGoogleGenerativeAI, 'ChatBedrock']:
        """Create an LLM instance based on the configured provider."""
        provider = self.config.llm_provider
        
        if provider == "google":
            return self._create_google_llm()
        elif provider == "aws_bedrock":
            return self._create_bedrock_llm()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def create_embedding_model(self) -> Union[GoogleGenerativeAIEmbeddings, 'BedrockEmbeddings']:
        """Create an embedding model instance based on the configured provider."""
        provider = self.config.llm_provider
        
        if provider == "google":
            return self._create_google_embeddings()
        elif provider == "aws_bedrock":
            return self._create_bedrock_embeddings()
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def _create_google_llm(self) -> ChatGoogleGenerativeAI:
        """Create a Google Gemini LLM instance."""
        try:
            logger.info(f"🤖 Initializing Google Gemini LLM: {self.config.llm_model}")
            
            return ChatGoogleGenerativeAI(
                model=self.config.llm_model,
                google_api_key=self.config.google_api_key,
                temperature=self.config.llm_temperature,
                convert_system_message_to_human=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini LLM: {e}")
            raise
    
    def _create_google_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Create Google embeddings instance."""
        try:
            logger.info(f"📊 Initializing Google embeddings: {self.config.embedding_model}")
            
            return GoogleGenerativeAIEmbeddings(
                model=self.config.embedding_model,
                google_api_key=self.config.google_api_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google embeddings: {e}")
            raise
    
    def _create_bedrock_llm(self):
        """Create an AWS Bedrock LLM instance."""
        try:
            # Import AWS Bedrock dependencies
            from langchain_aws import ChatBedrock
            import boto3
            
            logger.info(f"🤖 Initializing AWS Bedrock LLM: {self.config.aws_bedrock_model}")
            logger.info(f"📍 Using AWS Profile: {self.config.aws_profile}")
            logger.info(f"🌍 Using AWS Region: {self.config.aws_region}")
            
            # Create boto3 session with the specified profile
            session = boto3.Session(
                profile_name=self.config.aws_profile,
                region_name=self.config.aws_region,
                
            )
            
            # Create Bedrock client
            bedrock_client = session.client(
                service_name='bedrock-runtime',
                region_name=self.config.aws_region
                
            )
            
            # Create ChatBedrock instance
            return ChatBedrock(
                client=bedrock_client,
                model_id=self.config.aws_bedrock_model,
                model_kwargs={
                    "temperature": self.config.llm_temperature,
                    "max_tokens": 4096
                }
            )
            
        except ImportError as e:
            logger.error("AWS Bedrock dependencies not installed. Install with: pip install langchain-aws boto3")
            raise ImportError("Missing AWS dependencies. Run: pip install langchain-aws boto3") from e
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock LLM: {e}")
            raise
    
    def _create_bedrock_embeddings(self):
        """Create AWS Bedrock embeddings instance."""
        try:
            # Import AWS Bedrock dependencies
            from langchain_aws import BedrockEmbeddings
            import boto3
            
            logger.info("📊 Initializing AWS Bedrock embeddings")
            
            # Create boto3 session with SSL configuration
            use_ssl_bypass = os.getenv('CONTEXTLY_SSL_BYPASS', 'false').lower() == 'true'
            session = SSLConfig.create_session_with_ssl_config(
                profile_name=self.config.aws_profile,
                region_name=self.config.aws_region,
                verify_ssl=not use_ssl_bypass
            )
            
            # Create Bedrock client with SSL configuration
            boto_config = SSLConfig.get_boto_config(verify_ssl=not use_ssl_bypass)
            bedrock_client = session.client(
                service_name='bedrock-runtime',
                region_name=self.config.aws_region,
                config=boto_config
            )
            
            # Use Amazon Titan embeddings model
            return BedrockEmbeddings(
                client=bedrock_client,
                model_id="amazon.titan-embed-text-v1"
            )
            
        except ImportError as e:
            logger.error("AWS Bedrock dependencies not installed. Install with: pip install langchain-aws boto3")
            # Fallback to Google embeddings if AWS not available
            logger.info("Falling back to Google embeddings")
            return self._create_google_embeddings()
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock embeddings: {e}")
            # Fallback to Google embeddings
            logger.info("Falling back to Google embeddings")
            return self._create_google_embeddings()
    
    def get_provider_info(self) -> dict:
        """Get information about the current LLM provider configuration."""
        provider = self.config.llm_provider
        
        info = {
            "provider": provider,
            "model": self.config.llm_model,
            "temperature": self.config.llm_temperature
        }
        
        if provider == "google":
            info.update({
                "embedding_model": self.config.embedding_model,
                "api_key_configured": bool(self.config.google_api_key)
            })
        elif provider == "aws_bedrock":
            info.update({
                "aws_profile": self.config.aws_profile,
                "aws_region": self.config.aws_region,
                "bedrock_model": self.config.aws_bedrock_model
            })
        
        return info


def create_llm_and_embeddings(config: Optional[Config] = None):
    """
    Convenience function to create LLM and embedding instances.
    
    Args:
        config: Optional Config instance. If not provided, creates a new one.
        
    Returns:
        Tuple of (llm, embeddings)
    """
    if config is None:
        config = Config()
    
    factory = LLMFactory(config)
    llm = factory.create_llm()
    embeddings = factory.create_embedding_model()
    
    return llm, embeddings