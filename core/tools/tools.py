from langchain_core.tools import tool, StructuredTool
from tools.add_tool import get_tool

def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(get_tool())

    return tools