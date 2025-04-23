import os
from dotenv import load_dotenv
from phoenix.otel import register

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")



#configure pheonix otel
os.environ['PHOENIX_PROJECT_NAME'] = "Jarvis"
tracer_provider = register(
    endpoint="http://phoenix:4317",  # Sends traces using gRPC
    auto_instrument=True,
) 

if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")

