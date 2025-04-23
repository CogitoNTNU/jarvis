from langchain_openai import ChatOpenAI
from ai_agents.model import Model, LLMType
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    temperature = 0
    max_tokens = 2048
    model: Model
    llm_type: LLMType

    def __init__(self, model: Model):
        self.model = model
    
    def get_llm(self):
        try:
            if self.model[1] == LLMType.chat_open_ai:
                logger.info(f"Initializing ChatOpenAI with model: {self.model[0]}")
                
                # Check for API key
                if not os.environ.get("OPENAI_API_KEY"):
                    logger.error("OPENAI_API_KEY environment variable not found")
                    raise ValueError("Missing OPENAI_API_KEY environment variable")
                    
                self.llm = ChatOpenAI(
                    model=self.model[0],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    request_timeout=30,  # Add timeout to prevent hanging
                )
                logger.info("ChatOpenAI initialized successfully")
            else:
                logger.error(f"Unsupported LLM type: {self.model[1]}")
                raise ValueError(f"Unsupported LLM type: {self.model[1]}")
                
            return self.llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise



