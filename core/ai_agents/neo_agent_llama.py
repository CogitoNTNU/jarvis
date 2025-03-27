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

# Updated Ollama implementation
#from langchain_community.chat_models.ollama import ChatOllama

class NeoAgentLlama:
    def __init__(self):
        print("""
------------------------------
Instantiated NeoAgent Ollama....
------------------------------
        """)
        system_prompt = "You are Jarvis, an AI assistant here to help the human accomplish tasks. Respond in a conversational, natural style that sounds good when spoken aloud. Keep responses short and to the point, using clear, engaging language. When explaining your thought process, be concise and only describe essential steps to maintain a conversational flow."
        
        # Mistral-small can do up to 32768 context tokens but uses 5GB more VRAM. Thus using CPU and going from 40s to 4m 30s on a long-prompt or yt summary on 16GB card.
        model = ChatOllama(model="mistral-small", temperature=0, base_url="http://localhost:11434", num_ctx=2048)
        memory = MemorySaver()
        
        tools = [add, youtube_transcript]

        if os.getenv("TAVILY_API_KEY"):
            #tavily = TavilySearchResults(max_results=2)
            #tools.append(tavily)
            print('tavily disabled')
        else:
            print("TAVILY_API_KEY does not exist.")
        
        tool_node = ToolNode(tools)
        
        # Binding tools to the model
        model = model.bind_tools(tools=tools)

        class State(TypedDict):
            messages: Annotated[list, add_messages]

        graph_builder = StateGraph(State)

        def executive_node(state: State):
            if not state["messages"]:
                state["messages"] = [("system", system_prompt)]
            return {"messages": [model.invoke(state["messages"])]}
        
        graph_builder.add_node("executive_node", executive_node) 
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_conditional_edges("executive_node", tools_condition)
        graph_builder.add_edge("tools", "executive_node")
        graph_builder.set_entry_point("executive_node")
        self.graph = graph_builder.compile(checkpointer=memory)

        with open("neoagent.png", 'wb') as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    async def run(self, user_prompt: str, socketio):
        config = {"configurable": {"thread_id": "1"}}
        try:
            input = {"messages": [("human", user_prompt)]}
            socketio.emit("start_message", " ")
            async for event in self.graph.astream_events(input, config, version='v2'):
                event_type = event.get('event')
                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]
                    if isinstance(ai_message, AIMessage):
                        print(ai_message)
                        if 'tool_calls' in ai_message.additional_kwargs:
                            try:
                                tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
                                socketio.emit("tool_call", tool_call)
                                continue
                            except Exception as e:
                                return e
                        socketio.emit("chunk", ai_message.content)
                        socketio.emit("tokens", ai_message.usage_metadata['total_tokens'])
                        continue
                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]
                    if isinstance(tool_response, ToolMessage):
                        socketio.emit("tool_response", tool_response.content)
                        continue
            return ai_message.content #send this to MongoDB
        except Exception as e:
            print(e)
            return e
