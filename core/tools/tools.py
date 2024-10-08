from langchain_core.tools import tool, StructuredTool
import tools.add_tool as add_tool
import tools.web_search as web_search
import tools.find_files as find_files
import tools.read_file as read_file
import tools.read_pdf as read_pdf
import tools.weather as weather

def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(web_search.get_tool())
    tools.append(find_files.get_tool())
    tools.append(read_file.get_tool())
    tools.append(read_pdf.get_tool())
    tools.append(weather.get_tool())
    

    return tools