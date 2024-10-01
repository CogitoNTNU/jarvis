from openai import OpenAI
import dotenv
import os
import json
import config

dotenv.load_dotenv()

def get_perplexity_response(user_query):
    messages = [
        {
            "role": "system",
            "content": "You are an artificial intelligence assistant that will present concise up to date information about the user's query.",
        },
        {
            "role": "user",
            "content": user_query,
        },
    ]

    client = OpenAI(api_key=config.PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3.1-sonar-small-128k-online",
        messages=messages,
        temperature=0.0,
    )
    data = response.json()
    message = json.loads(data)["choices"][0]["message"]["content"]

    return message
