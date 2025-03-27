from typing import Annotated
from typing_extensions import TypedDict
import os

from fastapi.websockets import WebSocket

from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition

from ai_agents.model import Model #Models for chatGPT

# Premade tool imports
from langchain_community.tools.tavily_search import TavilySearchResults
# Custom tool imports
from tools.add_tool import add # Adds 2 numbers together
from tools.youtube_transcript import youtube_transcript
from tools.vision import vision
#Add more tools here (manually I guess?)

from ai_agents.WebSocketAgent import WebSocketAgent # Superclass

class NeoThinkAgent(WebSocketAgent):
    def __init__(self):
        print("Instantiated NeoAgent....")
        system_prompt = "You are Jarvis, an AI assistant here to help the human accomplish tasks. Respond in a conversational, natural style that sounds good when spoken aloud. Keep responses short and to the point, using clear, engaging language. When explaining your thought process, be concise and only describe essential steps to maintain a conversational flow."
        # Defining the model TODO: Make this configurable with Llama, Grok, Gemini, Claude
        model = ChatOpenAI(
            model = Model.gpt_4o_mini[0],
            temperature=0,
            max_tokens=16384, # Max tokens for mini. For gpt4o it's 128k
        ) # Using ChatGPT hardcoded (TODO: Make this dynamic)
        # Defining the checkpoint memory saver.
        memory = MemorySaver()
        # Tools list
        tools = [add, youtube_transcript, vision]

        if os.getenv("TAVILY_API_KEY"):
            # Defining the tavily web-search tool
            tavily = TavilySearchResults(max_results=2)
            tools.append(tavily)
        else:
            print("TAVILY_API_KEY does not exist.")
            
        tool_node = ToolNode(tools)
        llm_with_tools = model.bind_tools(tools)

        class State(TypedDict):
            messages: Annotated[list, add_messages]

        graph_builder = StateGraph(State)

        #Executive node that thinks about the problem or query at hand
        def executive_node(state: State):
            if not state["messages"]:
                state["messages"] = [("system", system_prompt)]
            return {"messages": [llm_with_tools.invoke(state["messages"])]}
        
        graph_builder.add_node("executive_node", executive_node) 
        graph_builder.add_node("tools", tool_node) # The prebuilt tool node added as "tools"

        graph_builder.add_conditional_edges(
            "executive_node",
            tools_condition,
        )

        # add conditionals, entry point and compile the graph. Exit is defined in the tools node if required.
        graph_builder.add_edge("tools", "executive_node")
        graph_builder.set_entry_point("executive_node")
        self.graph = graph_builder.compile(checkpointer=memory)

        # Draws the graph visually
        # with open("neoagent.png", 'wb') as f:
          #  f.write(self.graph.get_graph().draw_mermaid_png())

    # Streams graph updates using websockets.
    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Remove. This is just a placeholder
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)