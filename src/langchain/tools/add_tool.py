from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

@tool
def add(a: int, b: int) -> int:
    """
    Add two integers.

    Args: 
        a: First integer
        b: Second integer
    """
    return a + b

def get_tool() -> StructuredTool:
    return add