from openai import OpenAI
import dotenv
import os

dotenv.load_dotenv()

YOUR_API_KEY = os.getenv("PERPLEXITY_API_KEY")

messages = [
    {
        "role": "system",
        "content": (
            "You are an artificial intelligence assistant and you need to "
            "engage in a helpful, detailed, polite conversation with a user."
        ),
    },
    {
        "role": "user",
        "content": (
            "Hvordan blir været i Trondheim i morgen?"
        ),
    },
]

client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

# chat completion without streaming
response = client.chat.completions.create(
    model="llama-3.1-sonar-small-128k-online",
    messages=messages,
)
print(response)

# chat completion with streaming
"""
response_stream = client.chat.completions.create(
    model="llama-3.1-sonar-small-128k-online",
    messages=messages,
    stream=True,
)
for response in response_stream:
    print(response)
"""
