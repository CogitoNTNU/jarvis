import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config import get_calendar_service, GOOGLE_CALENDAR_ID

load_dotenv()

class read_calendar_events_parameters(BaseModel):   
    time_min: str = Field(
        description="Start time to fetch events from in ISO format(YYYY-MM-DDTHH:MM:SS), the current time can be collected from current_time_iso_format tool",
        example="2024-10-16T00:00:00"
    )
    time_max: str = Field(
        description="End time to fetch events until in ISO format(YYYY-MM-DDTHH:MM:SS)",
        example="2024-10-16T23:59:59"
        ,
    )
    maxResults: int = Field(
        description="Maximum number of events to fetch",
        example=10
    )

@tool("read_calendar_events", args_schema=read_calendar_events_parameters)
def read_calendar_events(time_min: str, time_max: str, maxResults: int = 10) -> str:
    """
    Use this tool to read events from the calendar within a specified time range.
    """
    service = get_calendar_service()

    dt_min =datetime.strptime(time_min, '%Y-%m-%dT%H:%M:%S')
    dt_max =datetime.strptime(time_max, '%Y-%m-%dT%H:%M:%S')
    dt_utc_min = dt_min.replace(tzinfo=timezone.utc)
    dt_utc_max = dt_max.replace(tzinfo=timezone.utc)
    time_min = dt_utc_min.isoformat()
    time_max = dt_utc_max.isoformat()

    events_result = service.events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=maxResults,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    if not events:
        return "No events found in the specified time range."
    
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        event_details = (
            f"Event: {event['summary']}\n"
            f"Start: {start}\n"
            f"End: {end}\n"
            f"Location: {event.get('location', 'No location specified')}\n"
            f"Description: {event.get('description', 'No description provided')}\n"
            f"Link: {event.get('htmlLink', 'No link available')}\n"
        )
        formatted_events.append(event_details)
    
    return "\n".join(formatted_events)

def get_tool() -> StructuredTool:
    return read_calendar_events

if __name__ == "__main__":
    # Example usage
    now = datetime.now(timezone.utc)
    
    time_min = now.isoformat() 
    time_max = (now + timedelta(days=7)).isoformat()
    print(time_min, time_max)
    result = read_calendar_events(time_min, time_max)
    print(result)