import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

def get_calendar_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_AUTH_KEY"), scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=creds)
    return service

@tool   # Remove for testing
def create_calendar_event(summary: str, location: str, description: str, start_time: str, end_time: str) -> str:
    """
    Use this tool to create an event in the calendar.

    Args:
        summary(string): Event title.
        location(string): Event location. Default to "Anywhere but not nowhere" if user does not provide a location.
        description(string): Event description.
        start_time(string): Event start time in ISO format(YYYY-MM-DDTHH:MM:SSZ)
        end_time(string): Event end time in ISO format(YYYY-MM-DDTHH:MM:SSZ)

    Returns:
        Confirmation message with event details.
    """
    service = get_calendar_service()
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC",
        },
    }

    event_result = service.events().insert(calendarId=os.getenv("GOOGLE_CALENDAR_ID"), body=event).execute()
    return f"Event created: {event_result.get('htmlLink')}"

def get_tool() -> StructuredTool:
    return create_calendar_event

if __name__ == "__main__":
    # Example usage
    summary = "Test Event"
    location = "Online"
    description = "This is a test event created by the Google Calendar tool"
    start_time = "2024-10-09T12:00:00Z"  # Format: YYYY-MM-DDTHH:MM:SSZ
    end_time = "2024-10-09T15:00:00Z"    # Format: YYYY-MM-DDTHH:MM:SSZ
    
    result = create_calendar_event(summary, location, description, start_time, end_time)
    print(result)