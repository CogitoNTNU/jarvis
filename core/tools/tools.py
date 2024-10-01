from langchain_core.tools import tool, StructuredTool
import tools.add_tool as add_tool
import tools.web_search as web_search

def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(web_search.get_tool())

    return tools