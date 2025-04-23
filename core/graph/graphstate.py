from typing import Annotated, TypedDict, Literal
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    data: dict
    tool_decision: Literal["use_tool", "generate"]
    agent_decision: Literal["perplexity", "calendar", "other"]
    calendar_events: dict  # Store events passed from calendar subgraph


class CalendarGraphState(TypedDict):
    messages: Annotated[list, add_messages]
    calendar_decision: Literal["use_calendar_tool", "return_to_jarvis"]
    calendar_data: dict
    calendar_events: dict  # Storage for created/read events to prevent duplicates
