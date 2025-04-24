import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config import get_calendar_service, GOOGLE_CALENDAR_ID

load_dotenv()

class create_calendar_event_parameters(BaseModel):
    summary: str = Field(description="Event title", example="Test Event")
    location: str = Field(description="Event location", example="Online")
    description: str = Field(description="Event description", example="This is a test event created by the Google Calendar tool")
    start_time: str = Field(description="Event start time in ISO format(YYYY-MM-DDTHH:MM:SS), the current time can be collected from current_time_iso_format tool", example="2024-10-16T12:00:00Z")
    end_time: str = Field(description="Event end time in ISO format(YYYY-MM-DDTHH:MM:SS), can use add_time tool to add for example an hour", example="2024-10-16T15:00:00Z")

@tool("create_calendar_event",args_schema=create_calendar_event_parameters)
def create_calendar_event(summary: str, location: str, description: str, start_time: str, end_time: str) -> str:
    """
    Use this tool to create an event in the calendar.
    """
    service = get_calendar_service()
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start_time,
            "timeZone": "Europe/Oslo",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Europe/Oslo",
        },
    }

    event_result = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
    return f"Event created: {event_result.get('htmlLink')}"

def get_tool() -> StructuredTool:
    return create_calendar_event

if __name__ == "__main__":
    # Example usage
    summary = "Test Event"
    location = "Online"
    description = "This is a test event created by the Google Calendar tool"
    start_time = "2024-11-04T12:00:00"  # Format: YYYY-MM-DDTHH:MM:SS
    end_time = "2024-11-04T15:00:00"    # Format: YYYY-MM-DDTHH:MM:SS
    
    result = create_calendar_event(summary, location, description, start_time, end_time)
    print(result)