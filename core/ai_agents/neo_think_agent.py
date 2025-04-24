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
from tools.painter import painter
#Add more tools here (manually I guess?)

from ai_agents.WebSocketAgent import WebSocketAgent # Superclass

class NeoThinkAgent(WebSocketAgent):
    def __init__(self):
        print("Instantiated NeoAgent....")
        system_prompt = """
        You are Jarvis, an AI assistant here to help the human accomplish tasks. 
        Respond in a conversational, natural style that sounds good when spoken aloud. 
        Keep responses short and to the point, using clear, engaging language. 
        When explaining your thought process, be concise and only describe essential steps to maintain a conversational flow.

        ### Image Generation Rules:
        - If a response would be **more engaging, clear, or creative** with a visual, generate an image.
        - You **do not need explicit permission** to generate an image.
        - When generating an image, describe it concisely first, then trigger the painter tool.
        - If an image is unnecessary, respond with text only.
        """
        # Defining the model TODO: Make this configurable with Llama, Grok, Gemini, Claude
        model = ChatOpenAI(
            model = Model.gpt_4_1_mini[0],
            temperature=0,
            max_tokens=16384, # Max tokens for mini. For gpt4o it's 128k
        ) # Using ChatGPT hardcoded (TODO: Make this dynamic)

        memory = MemorySaver()

        # Tools
        tools = [add, youtube_transcript, vision, painter]
        tool_node = ToolNode(tools)
        llm_with_tools = model.bind_tools(tools)

        # State for the graph
        class State(TypedDict):
            messages: Annotated[list, add_messages]

        #Executive node that thinks about the problem or query at hand
        def executive_node(state: State):
            if not state["messages"]:
                state["messages"] = [("system", system_prompt)]
            llm_answer = llm_with_tools.invoke(state["messages"])
            return {"messages": [llm_answer]}

        graph_builder = StateGraph(State)

        graph_builder.add_node("executive_node", executive_node) # Entry Node 
        graph_builder.add_node("tools", tool_node) # The prebuilt tool node added as "tools"

        graph_builder.add_conditional_edges("executive_node", tools_condition) # tools_condition checks if the last call was a tool call and routes to the executive_node
        graph_builder.add_edge("tools", "executive_node") # Transitions from tools to executive_node. An edge that transitions to the start_node will always go to end after.

        graph_builder.set_entry_point("executive_node")
        self.graph = graph_builder.compile() # checkpointer=memory

        # Draws the graph visually
        # with open("neoagent.png", 'wb') as f:
          #  f.write(self.graph.get_graph().draw_mermaid_png())

    # Streams graph updates using websockets.
    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Thread ID should be dynamic and not hardcoded. Thread_id should be a unique id for each conversation.
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)