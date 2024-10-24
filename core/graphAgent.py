from langchain_openai import ChatOpenAI
from graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from models import Model
import json
from config import OPENAI_API_KEY
from Agents.simpleagent import SimpleAgent
from graphtools import graphtool
import asyncio
from time import sleep
import functools

class Graph:
    def __init__(self):
        LANGCHAIN_TRACING_V2: str = "true"
        
        self.llm = SimpleAgent.llm
        self.llm_with_tools = self.llm.bind_tools(get_tools())

        self.workflow = StateGraph(GraphState)

        self.workflow.add_node("chatbot", self.chatbot)
        self.workflow.add_node("tools", ToolNode(get_tools()))

        self.workflow.add_edge(START, "chatbot")
        self.workflow.add_edge("tools", "chatbot")
        self.workflow.add_edge("chatbot", END)

        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "chatbot",
            tools_condition
        )
        self.graph = self.workflow.compile()

        with open("graph_node_network.png", 'wb') as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}
    

# UNFINISHED
    def run_stream_only(self, user_prompt: str):
        """
        Run the agent, returning a token stream.
        """
        print('Running stream...')
        print(user_prompt)
        print(type(user_prompt))
        for chunk in self.llm.stream(user_prompt):
            yield chunk.content

    #for running the agent comment out for testing in terminal
    async def run(self, user_prompt: str, socketio):
        """
        Run the agent with a user prompt and emit the response and total tokens via socket
        """
        try:
            input = {"messages": [("human", user_prompt)]}
            socketio.emit("start_message", " ")
            async for event in self.graph.astream_events(input, version='v2'):
                event_type = event.get('event')

                # Focuses only on the 'on_chain_stream'-events. 
                # There may be better events to base the response on
                if event_type == 'on_chain_stream' and event['name'] == 'LangGraph':
                    chunk = event['data']['chunk']
                    if 'chatbot' in chunk:
                        ai_message = event['data']['chunk']['chatbot']['messages'][-1]

                        if isinstance(ai_message, AIMessage):
                            if 'tool_calls' in ai_message.additional_kwargs:
                                tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
                                #tool_call_id = ai_message.additional_kwargs['call_tool'][0]['tool_call_id']
                                socketio.emit("tool_call", tool_call)
                                continue
                        
                            socketio.emit("chunk", ai_message.content)
                            socketio.emit("tokens", ai_message.usage_metadata['total_tokens'])
                            continue
                
                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]

                    if isinstance(tool_response, ToolMessage):
                        socketio.emit("tool_response", tool_response.content)
                        continue

            return "success"
        except Exception as e:
            print(e)
            return "error"