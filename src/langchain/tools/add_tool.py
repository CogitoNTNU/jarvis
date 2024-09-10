from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """
    Add two integers.

    Args: 
        a: First integer
        b: Second integer
    """
    return a + b

def get_tool() -> list[(...) -> Any]: # type: ignore
    return [add]