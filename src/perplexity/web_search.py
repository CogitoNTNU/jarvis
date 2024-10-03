from openai import OpenAI
import dotenv, os, json

dotenv.load_dotenv()

YOUR_API_KEY = os.getenv("PERPLEXITY_API_KEY")

messages = [
    {
        "role": "system",
        "content": (
            "You are an artificial intelligence assistant that will present concise up to date information about the user's query. "
            
        ),
    },
    {
        "role": "user",
        "content": (
            "Hvordan er været i Trondheim i morgen?"
        ),
    },
]

client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

# chat completion without streaming
response = client.chat.completions.create(
    model="llama-3.1-sonar-small-128k-online",
    messages=messages,
    temperature=0.0,
)
data = response.json()
print(data)
message = json.loads(data)["choices"][0]["message"]["content"]
print(message)


# chat completion with streaming
"""
response_stream = client.chat.completions.create(
    model="llama-3.1-sonar-small-128k-online",
    messages=messages,
    stream=True,
)
for response in response_stream:
    if response.choices[0].delta.content is not None:
        print(response.choices[0].delta.content, end='')
print()  # Add a newline at the end
"""
