import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool
from datetime import datetime




#Dormamu I've come to bargain
@tool("current_time_iso_format")
def current_time_iso_format(basetool):
    """
    Use this tool to create get the current local  time in ISO format.
    you WANT to use this tool to get the time in ISO format when it is required.

    Returns:
        str: The current time in ISO format.
    """
    time = datetime.now().replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
    return time

def get_tool() -> StructuredTool:
    return current_time_iso_format