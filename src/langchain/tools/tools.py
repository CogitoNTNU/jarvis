from langchain_core.tools import tool
from src.langchain.tools.add_tool import *

def get_tools() -> List[(...) -> Any]:  # type: ignore
    tools = []
    tools.append(get_tool)

    return tools