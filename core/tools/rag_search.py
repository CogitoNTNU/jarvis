from rag import similarity_search
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from typing import List, Tuple


@tool 
def rag_search(query: str)-> List[Tuple[str, float]]:
    """
    Use this tool to get relevant conversation history

    Args:
        query (str): The query to search for 

    Returns:
        List[Tuple[str, float]]: Relevant chat history 
    """
    result = similarity_search(query, "1")

    return result


def get_tool() -> StructuredTool:
    return rag_search