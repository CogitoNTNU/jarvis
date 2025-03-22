import requests
from typing import Annotated
from langchain_core.tools import tool
from langchain.tools import StructuredTool

@tool
def get_crypto_price(crypto: Annotated[str, "Name of the cryptocurrency, e.g. 'bitcoin', 'ethereum'"]) -> str:
    """
    Use this tool to get the current price of a cryptocurrency in USD.
    The name should be lowercase and follow CoinGecko naming (e.g., 'bitcoin', 'ethereum').
    
    Args:
        crypto (str): The name of the cryptocurrency to look up.

    Returns:
        str: The current price in USD.
    """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd"
    
    response = requests.get(url)
    
    if response.status_code != 200:
        return f"Failed to fetch price. Status code: {response.status_code}"

    data = response.json()
    try:
        price = data[crypto]["usd"]
        return f"The current price of {crypto} is ${price:.2f} USD."
    except KeyError:
        return f"Cryptocurrency '{crypto}' not found."

def get_tool() -> StructuredTool:
    return get_crypto_price