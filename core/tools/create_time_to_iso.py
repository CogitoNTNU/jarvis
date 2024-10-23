import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool
from datetime import datetime

class create_time_iso_format_parameters(BaseModel):
    year: int = Field(description="The year of the time", example= [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030])
    month: int = Field(description="The month of the time", example= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    day: int = Field(description="The day of the time", example= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31])
    hour: int = Field(description="The hour of the time", example= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
    minute: int = Field(description="The minute of the time", example= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60])
    second: int = Field(description="The second of the time", example= [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60])

@tool("create_time_iso_format",args_schema=create_time_iso_format_parameters)
def create_time_iso_format(year: int, month: int, day: int, hour: int, minute: int = 00, second: int = 00):
    """
    Use this tool to create time to iso format.
    you WANT to get a some specific time in ISO format when it is required.

    Returns:
        str: The your inputed time in ISO format.
    """
    time = datetime(year, month, day, hour, minute, second).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
    return time

def get_tool() -> StructuredTool:
    return create_time_iso_format
