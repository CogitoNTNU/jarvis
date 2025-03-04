import os
from dotenv import load_dotenv
from phoenix.otel import register

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


#add langsmith api to env as LANGSMITH_API_KEY = "your_api_key" on EU server
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "no_key")
print(LANGSMITH_API_KEY)

#configure pheonix otel
os.environ['PHOENIX_PROJECT_NAME'] = "Jarvis"
tracer_provider = register(
    endpoint="http://phoenix:4317",  # Sends traces using gRPC
    auto_instrument=True,
) 

if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")
    if(LANGSMITH_API_KEY):
        print(f"[INFO] LANGSMITH_API_KEY: {LANGSMITH_API_KEY}")

