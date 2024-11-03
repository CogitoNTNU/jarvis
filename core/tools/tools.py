from langchain_core.tools import tool, StructuredTool
import tools.add_tool as add_tool
import tools.web_search as web_search
import tools.find_files as find_files
import tools.read_file as read_file
import tools.read_pdf as read_pdf
import tools.weather as weather
import tools.google_calender_create as create_calender_event
import tools.google_calender_read as read_calender_event
import tools.create_time_to_iso as create_time_to_iso_format
import tools.current_time_iso as current_time_iso_format
import tools.add_time as add_time


def get_tools() -> list[StructuredTool]:
    tools = []
    tools.append(add_tool.get_tool())
    tools.append(web_search.get_tool())
    tools.append(find_files.get_tool())
    tools.append(read_file.get_tool())
    tools.append(read_pdf.get_tool())
    tools.append(weather.get_tool())
    tools.append(create_calender_event.get_tool())
    tools.append(read_calender_event.get_tool())
    tools.append(create_time_to_iso_format.get_tool())
    tools.append(current_time_iso_format.get_tool())

    return tools
