import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool
from datetime import datetime, timedelta



class add_time_parameters(BaseModel):
    time_iso_format: str = Field(description="The time in ISO format", example="2022-12-12T12:00:00")
    year: int = Field(default=0, description="The year to add (can be empty, defaults to 0)", example=[None, 1, 2])
    month: int = Field(default=0, description="The month to add (can be empty, defaults to 0)", example=[None, 1, 2, 3, 6])
    day: int = Field(default=0, description="The day to add (can be empty, defaults to 0)", example=[None, 1, 7, 14, 30])
    hour: int = Field(default=0, description="The hour to add (can be empty, defaults to 0)", example=[None, 1, 2, 3, 12])
    minute: int = Field(default=0, description="The minute to add (can be empty, defaults to 0)", example=[None, 15, 30, 45, 60])
    second: int = Field(default=0, description="The second to add (can be empty, defaults to 0)", example=[None, 30, 60])
                                                                                                
@tool("add_time", args_schema=add_time_parameters)
def add_time(time_iso_format: str, year: int = 0, month: int = 0, day: int = 0, hour: int = 0, minute: int = 0, second: int = 0):
    """
    Use this tool to add time to the input ISO formatted time.
    Useful when you want to increase the time between two times, for example for creating a calendar event.

    Returns:
        str: The current time plus the time you added in ISO format.
    """
    # Handle Z suffix if present
    if time_iso_format.endswith('Z'):
        time_iso_format = time_iso_format[:-1]
        add_z = True
    else:
        add_z = False
        
    # Parse the input time
    time = datetime.fromisoformat(time_iso_format)
    
    # Add the specified time components
    time_add = time + timedelta(days=day, hours=hour, minutes=minute, seconds=second)
    
    # For years and months (not supported by timedelta)
    if year != 0:
        time_add = time_add.replace(year=time_add.year + year)
    if month != 0:
        new_month = time_add.month + month
        years_to_add = (new_month - 1) // 12
        final_month = ((new_month - 1) % 12) + 1
        time_add = time_add.replace(year=time_add.year + years_to_add, month=final_month)
    
    # Format the result back to ISO format
    new_time = time_add.isoformat()
    
    # Add Z suffix if it was in the original input
    if add_z:
        new_time += 'Z'
        
    return new_time

def get_tool() -> StructuredTool:
    return add_time