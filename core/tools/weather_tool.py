from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

@tool
def get_forecast(a: int, b: int) -> int:
    """
    Add two integers.

    Args: 
        a: First integer
        b: Second integer
    """
    return a + b

def get_tool() -> StructuredTool:
    return get_forecast