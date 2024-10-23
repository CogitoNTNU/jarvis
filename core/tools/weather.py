from openai import OpenAI
import dotenv
import config
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from pydantic import BaseModel, Field

dotenv.load_dotenv()


class weather_forecast_parameters(BaseModel):
    user_query: str = Field(description="The query to search for.", 
                            examples=["Hvordan blir været i Trondheim i morgen?","Hvordan blir været på Kapp til helgen?", "Hvordan blir været i Bergen 02.11.2024?"])
@tool("weather_forecast", args_schema=weather_forecast_parameters)
def weather_forecast(user_query: str) -> str:
    """
    Use this tool to search for weather forecasts. user_query must be a string and formualated as a question.'
    Example: Hvordan blir været i Trondheim i morgen?
    Example: Hvordan blir været på Kapp til helgen?
    Example: Hvordan blir været i Bergen 02.11.2024?

    Args:
        user_query: The query(string) to search for.
    """

    messages = [
        {
            "role": "user",
            "content": user_query,
        },
    ]

    client = OpenAI(api_key=config.PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3.1-sonar-large-128k-online",
        messages=messages,
        temperature=0.0,
    )
    
    message = response.choices[0].message.content

    return message

def get_tool() -> StructuredTool:
    return weather_forecast
