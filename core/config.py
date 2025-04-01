import os
from modules.logging_utils import logger
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

#add langsmith api to env as LANGSMITH_API_KEY = "your_api_key" on EU server
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "no_key")
logger.info(LANGSMITH_API_KEY)

if __name__ == "__main__":
    logger.info(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")
    if(LANGSMITH_API_KEY):
        logger.info(f"[INFO] LANGSMITH_API_KEY: {LANGSMITH_API_KEY}")