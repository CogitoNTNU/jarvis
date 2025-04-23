from langchain_openai import ChatOpenAI
from ai_agents.model import Model, LLMType
import os
import logging
from config import STREAM_ENABLED, STREAM_OPTIONS  # Add import for streaming config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agent:
    temperature = 0
    max_tokens = 2048
    model: Model
    llm_type: LLMType
    
    # Model-specific configurations
    MODEL_CONFIGS = {
        "gpt-4o-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "gpt-4o": {
            "max_tokens": 8192,
            "temperature": 0.7,
        },
        "gpt-3.5-turbo": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "o3-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "o4-mini": {
            "temperature": 1,
        },
        "gpt-4-1-mini": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "gpt-4o-mini_": {
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        # Add more models as needed
    }

    def __init__(self, model: Model, override_temp: float = None):
        self.model = model
        self.override_temp = override_temp

    def get_llm(self):
        try:
            if self.model[1] == LLMType.chat_open_ai:
                model_name = self.model[0]
                logger.info(f"Initializing ChatOpenAI with model: {model_name}")
                
                # Check for API key
                if not os.environ.get("OPENAI_API_KEY"):
                    logger.error("OPENAI_API_KEY environment variable not found")
                    raise ValueError("Missing OPENAI_API_KEY environment variable")
                
                # Start with minimal required parameters
                params = {
                    "model": model_name,
                    "request_timeout": 30,
                    "streaming": STREAM_ENABLED,  # Add streaming parameter
                    "stream_options": STREAM_OPTIONS,  # Add stream options for token tracking
                }
                
                # Apply model-specific parameters if available
                if model_name in self.MODEL_CONFIGS:
                    model_params = self.MODEL_CONFIGS[model_name].copy()
                    params.update(model_params)
                    logger.info(f"Applied specific configuration for model: {model_name}")
                else:
                    # Use default temperature only if no specific config exists
                    params["temperature"] = self.temperature
                    logger.info(f"No specific configuration found for {model_name}, using defaults")
                
                # Apply temperature override if provided
                if self.override_temp is not None:
                    params["temperature"] = self.override_temp
                    logger.info(f"Overriding temperature with value: {self.override_temp}")
                
                logger.info(f"Initializing ChatOpenAI with parameters: {params}")
                self.llm = ChatOpenAI(**params)
                logger.info(f"ChatOpenAI initialized successfully")
            else:
                logger.error(f"Unsupported LLM type: {self.model[1]}")
                raise ValueError(f"Unsupported LLM type: {self.model[1]}")
                
            return self.llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise



