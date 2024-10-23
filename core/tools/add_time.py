import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool
from datetime import datetime, timedelta



class add_time_parameters(BaseModel):
    time_iso_format: str = Field(description="The time in ISO format", example= "2022-12-12T12:00:00Z")
    year: int = Field(description="The year of the time, can empty defults to 0", example= [None,2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030])
    month: int = Field(description="The month of the time, can empty defults to 0", example= [None,1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    day: int = Field(description="The day of the time, can empty defults to 0", example= [None,1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31])
    hour: int = Field(description="The hour of the time, can empty defults to 0", example= [None,1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
    minute: int = Field(description="The minute of the time, can empty defults to 0", example= [None,1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60])
    second: int = Field(description="The second of the time, can empty defults to 0", example= [None,1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60])
                                                                                                
@tool("add_time",args_schema=add_time_parameters)
def add_time(time_iso_format,year: int = 0, month: int = 0, day: int = 0, hour: int = 0, minute: int = 0, second: int = 0):
    """
    Use this tool to add time to the the inputet iso time.
    you WANT to use increase the the time between two times, for example for creating a calender event.

    Returns:
        str: The current time plus the time you added in ISO format.
    """
    time = datetime.strptime(time_iso_format, '%Y-%m-%dT%H:%M:%SZ')
    time_add= time + timedelta(year, month, day, hour, minute, second)
    new_time = time_add.strftime('%Y-%m-%dT%H:%M:%SZ')
    return new_time


def get_tool() -> StructuredTool:
    return add_time