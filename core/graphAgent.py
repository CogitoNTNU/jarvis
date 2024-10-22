from langchain_openai import ChatOpenAI
from graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage
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
        llm = SimpleAgent.llm
        proof_reader = graphtool.create_agent(
            llm,
            get_tools(),
            system_message="You should proof read the text before you send it to the user.",
        )
        proof_read_node = functools.partial(graphtool.agent_node, agent=proof_reader, name="proof_reader")
        simple_agent = graphtool.create_agent(
            llm,
            get_tools(),
            system_message="You should take the input of the user and use the tools available to you to generate a response.",
        )   
        simple_agent_node = functools.partial(graphtool.agent_node, agent=simple_agent, name="simple_agent")
        
        tool_node = ToolNode(get_tools())
        self.workflow = StateGraph(GraphState)
        # Adding nodes to the workflow
        self.workflow.add_node("simple_agent", simple_agent_node)
        self.workflow.add_node("proof_reader", proof_read_node)
        self.workflow.add_node("call_tool", tool_node)
        # TODO: Visualize these tools

        # Defining edges between nodes
        self.workflow.add_conditional_edges(
                    "simple_agent",
                    graphtool.router,
                    {"continue": "simple_agent", "call_tool": "call_tool", END: END},
                )       
        self.workflow.add_conditional_edges(
            "proof_reader",
            graphtool.router,
            {"continue": "proof_reader", "call_tool": "call_tool", END: END},
        )
        
        self.workflow.add_conditional_edges(
            "call_tool",
            # Each agent node updates the 'sender' field
            # the tool calling node does not, meaning
            # this edge will route back to the original agent
            # who invoked the tool
            lambda x: x["sender"],
            {
                "simple_agent": "simple_agent",
                "proof_reader": "proof_reader",
            },
        )
        self.workflow.add_edge(START, "simple_agent")
        self.workflow.add_edge("proof_reader", END)
        
        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "simple_agent",
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
                #print(event)
                event_type = event.get('event')

                # Focuses only on the 'on_chain_stream'-events. 
                # There may be better events to base the response on
                if event_type == 'on_chain_stream' and event['name'] == 'LangGraph':
                    chunk = event['data']['chunk']
                    if 'chatbot' in chunk:
                        ai_message = event['data']['chunk']['chatbot']['messages'][-1]

                        if 'tool_calls' in ai_message.additional_kwargs:
                            continue
                    
                        socketio.emit("chunk", ai_message.content)
                        socketio.emit("tokens", ai_message.usage_metadata['total_tokens'])
                            

            return "success"
        except Exception as e:
            print(e)
            return "error"

        # for event in self.graph.stream(input):
            #print(event)
            # for value in event.values():
            #     messages = value["messages"][-1]
            #     gathered = ""
            #     # if messages.content and not isinstance(messages, HumanMessage):
            #     #     print(messages.content, end="|", flush=True)

            #     if isinstance(messages, AIMessageChunk):
            #         if first:
            #             gathered = messages
            #             first = False
            #         else:
            #             gathered += messages

            #     if isinstance(messages, BaseMessage):
            #         total_tokens = messages.usage_metadata.get('total_tokens', 0)
            #         return messages.content, total_tokens