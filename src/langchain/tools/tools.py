from langchain_core.tools import tool
from tools.add_tool import *

def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(get_tool())

    return tools