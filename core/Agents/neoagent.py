from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

"""
# Updating the state requires creating a new state (following state immutability for history and checkpoints)

# Example function to increment a value
def increment_count(state: GraphState) -> GraphState:
    return GraphState(count=state["count"] + 1)

# To add a message to the state.
def add_message(state: GraphState, message: str, is_human: bool = True) -> GraphState:
    new_message = HumanMessage(content=message) if is_human else AIMessage(content=message)
    return GraphState(
        count=state["count"],
        messages=state["messages"] + [new_message]
    )

from langgraph.graph import StateGraph, END

def create_complex_graph():
    workflow = StateGraph(GraphState)
    
    def process_message(state: GraphState):
        last_message = state["messages"][-1].content if state["messages"] else "No messages yet"
        response = f"Received: {last_message}. Count is now {state['count'] + 1}"
        return {
            "count": state["count"] + 1,
            "messages": state["messages"] + [AIMessage(content=response)]
        }
    
    workflow.add_node("process", process_message)
    workflow.set_entry_point("process")
    workflow.add_edge("process", END)
    
    return workflow.compile()
"""