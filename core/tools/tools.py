from langchain_core.tools import tool, StructuredTool
import tools.add_tool as add_tool
import tools.web_search as web_search
import tools.find_files as find_files
import tools.read_file as read_file
import tools.read_pdf as read_pdf
import tools.weather as weather
import tools.google_calendar_create as create_calendar_event
import tools.google_calendar_read as read_calendar_event
import tools.create_time_to_iso as create_time_to_iso_format
import tools.current_time_iso as current_time_iso_format
import tools.add_time as add_time
import tools.rag_search as rag_search
import tools.krypto_time as krypto_tool


def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(web_search.get_tool())
    tools.append(find_files.get_tool())
    tools.append(read_file.get_tool())
    tools.append(read_pdf.get_tool())
    tools.append(weather.get_tool())
    tools.append(create_calendar_event.get_tool())
    tools.append(read_calendar_event.get_tool())
    tools.append(create_time_to_iso_format.get_tool())
    tools.append(current_time_iso_format.get_tool())
    tools.append(rag_search.get_tool())
    tools.append(krypto_tool.get_tool())

    return tools

def get_perplexity_based_tools() -> list[StructuredTool]:
    tools = []
    tools.append(weather.get_tool())
    tools.append(web_search.get_tool())
    tools.append(rag_search.get_tool())

    return tools

def calendar_based_tools() -> list[StructuredTool]: 
    tools = []
    tools.append(create_calendar_event.get_tool())
    tools.append(read_calendar_event.get_tool())
    tools.append(current_time_iso_format.get_tool())
    tools.append(create_time_to_iso_format.get_tool())
    tools.append(add_time.get_tool())

    return tools

def get_other_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(find_files.get_tool())
    tools.append(read_file.get_tool())
    tools.append(read_pdf.get_tool())
    tools.append(rag_search.get_tool())
    tools.append(krypto_tool.get_tool())


    return tools