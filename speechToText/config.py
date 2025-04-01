import os
from dotenv import load_dotenv
from tools.logging_utils import logger
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT_STT = os.getenv("PORT_STT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

#add langsmith api to env as LANGSMITH_API_KEY = "your_api_key" on EU server
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "no_key")

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://eu.api.smith.langchain.com"
try:
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
except:
    logger.info("No langsmith key found")

if __name__ == "__main__":
    logger.info(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")
    if(LANGSMITH_API_KEY):
        logger.info(f"[INFO] LANGSMITH_API_KEY: {LANGSMITH_API_KEY}")