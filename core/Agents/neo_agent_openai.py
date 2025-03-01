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

from agents.model import Model #Models for chatGPT

# Premade tool imports
from langchain_community.tools.tavily_search import TavilySearchResults
# Custom tool imports
from tools.add_tool import add # Adds 2 numbers together
from tools.youtube_transcript import youtube_transcript

"""
Neoagent uses the ReAct agent framework.
Simply put in steps:
1. 'Re' The agent reasons about the problem, and plans out steps to solve it.
2. 'Act' The agent acts upon the information gathered. Calling tools or interacting with systems based on the earlier reasoning.
3. 'Loop' If the problem is not adequately solved, the agent can reason and act recursively until a satisfying solution is reached.
ReAct is a simple multi-step agent architecture.
Smaller graphs are often better understood by the LLMs.
"""
class NeoAgent:
    def __init__(self):
        print("""
------------------------------
Instantiated NeoAgent....
------------------------------
            """)
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
        tools = [add, youtube_transcript]

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
        with open("neoagent.png", 'wb') as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

    # Streams graph updates using websockets.
    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Remove. This is just a placeholder
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    async def run(self, user_prompt: str, websocket: WebSocket):
        """
        Run the agent with a user prompt and send the response via FastAPI WebSockets.
        """
        config = {"configurable": {"thread_id": "1"}}

        try:
            input_data = {"messages": [("human", user_prompt)]}
            await websocket.send_json({"event": "start_message", "data": " "})

            async for event in self.graph.astream_events(input_data, config, version='v2'):
                event_type = event.get('event')

                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]

                    if isinstance(ai_message, AIMessage):
                        print(ai_message)

                        # Handle tool calls
                        if 'tool_calls' in ai_message.additional_kwargs:
                            try:
                                tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
                                await websocket.send_json({"event": "tool_call", "data": tool_call})
                                continue
                            except Exception as e:
                                print(f"Error processing tool call: {e}")
                                return str(e)

                        # Send AI message chunk
                        await websocket.send_json({"event": "chunk", "data": ai_message.content})

                        # Send token usage data
                        await websocket.send_json({"event": "tokens", "data": ai_message.usage_metadata['total_tokens']})
                        continue

                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]
                    if isinstance(tool_response, ToolMessage):
                        await websocket.send_json({"event": "tool_response", "data": tool_response.content})
                        continue

            return ai_message.content  # Send this to MongoDB
        except Exception as e:
            print(f"Error in AI processing: {e}")
            return str(e)

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