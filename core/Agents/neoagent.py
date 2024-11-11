from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode

from models import Model #Models for chatGPT


"""
Neoagent uses the ReAct agent framework.
Simply put in steps:
1. 'Re' The agent reasons about the problem, and plans out steps to solve it.
2. 'Act' The agent acts upon the information gathered. Calling tools or interacting with systems based on the earlier reasoning.
3. 'Loop' If the problem is not adequately solved, the agent can reason and act recursively until a satisfying solution is reached.
ReAct is a simple multi-step agent architecture.
Smaller graphs are often better understood by the LLMs.
"""

memory = MemorySaver()

@tool
def search(query: str):
    """Call to surf the web."""
    # This is a placeholder for the actual implementation
    # Don't let the LLM know this though 😊
    return "It's sunny in San Francisco, but you better look out if you're a Gemini 😈."

tools = [search]
tool_node = ToolNode(tools)
model = ChatOpenAI(
    model = Model.gpt_4o,
    temperature=0,
    max_tokens=16384, # Max tokens for mini. For gpt4o it's 128k
) # Using ChatGPT hardcoded (TODO: Make this dynamic)
bound_model = model.bind_tools(tools)

class State(TypedDict):
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