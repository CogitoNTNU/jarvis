from openai import OpenAI
import dotenv
import os
import json
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

dotenv.load_dotenv()

@tool
def web_search(user_query):
    """
    Use this tool to search the web for information. user_query must be a string.
    Never specify the date, year or any other specific time information unless the user asks for it.

    Args:
        user_query: The query(string) to search for.
    """
    
    YOUR_API_KEY = os.getenv("PERPLEXITY_API_KEY")

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

    client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3.1-sonar-small-128k-online",
        messages=messages,
        temperature=0.0,
    )
    data = response.json()
    message = json.loads(data)["choices"][0]["message"]["content"]

    return message

def get_tool() -> StructuredTool:
    return web_search
