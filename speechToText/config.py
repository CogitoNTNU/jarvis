import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT_STT = os.getenv("PORT_STT")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


if __name__ == "__main__":
    print(f"[INFO] OPENAI_API_KEY: {OPENAI_API_KEY}")