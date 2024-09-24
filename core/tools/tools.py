from langchain_core.tools import tool, StructuredTool
import tools.add_tool
import tools.weather_tool

def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(weather_tool.get_tool())

    return tools