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
