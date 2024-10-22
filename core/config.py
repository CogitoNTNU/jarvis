import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

#add langsmith api to env as LANGSMITH_API_KEY = "your_api_key" on EU server
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "no_key")

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://eu.api.smith.langchain.com"
try:
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
except:
    print("No langsmith key found")

if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")
    if(LANGSMITH_API_KEY):
        print(f"[INFO] LANGSMITH_API_KEY: {LANGSMITH_API_KEY}")