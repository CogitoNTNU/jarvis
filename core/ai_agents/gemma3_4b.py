from typing import Annotated
from typing_extensions import TypedDict
import os

from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition

from ai_agents.model import Model  # Models for chatGPT

# Premade tool imports
#from langchain_community.tools.tavily_search import TavilySearchResults
# Custom tool imports
from tools.add_tool import add  # Adds 2 numbers together
from tools.youtube_transcript import youtube_transcript

from langchain_ollama import ChatOllama

from ai_agents.WebSocketAgent import WebSocketAgent

# Updated Ollama implementation
#from langchain_community.chat_models.ollama import ChatOllama

class NeoAgentLlama(WebSocketAgent):
    def __init__(self):
        print("""Instantiated NeoAgent Ollama....""")
        # Mistral-small can do up to 32768 context tokens but uses 5GB more VRAM. Thus using CPU and going from 40s to 4m 30s on a long-prompt or yt summary on 16GB card.
        model = ChatOllama(model="gemma3", temperature=0, base_url="http://host.docker.internal:11434", num_ctx=2048)
        memory = MemorySaver()
        tools = [add, youtube_transcript]
        
        # Binding tools to the model
        # model = model.bind_tools(tools=tools)

        class State(TypedDict):
            messages: Annotated[list, add_messages]

        graph_builder = StateGraph(State)

        tool_node = ToolNode(tools)

        def executive_node(state: State):
            if not state["messages"]:
                state["messages"] = [("system", system_prompt)]
            return {"messages": [model.invoke(state["messages"])]}
        
        graph_builder.add_node("executive_node", executive_node) 
        #graph_builder.add_node("tools", tool_node)
        #graph_builder.add_conditional_edges("executive_node", tools_condition)
        #graph_builder.add_edge("tools", "executive_node")
        graph_builder.set_entry_point("executive_node")
        self.graph = graph_builder.compile(checkpointer=memory)

        #with open("neoagent.png", 'wb') as f:
        #    f.write(self.graph.get_graph().draw_mermaid_png())

    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)