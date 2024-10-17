from langchain_openai import ChatOpenAI
from graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage
from models import Model
import json
from config import OPENAI_API_KEY
from agent import Agent, Agent1 


class Graph:
    def __init__(self):
        LANGCHAIN_TRACING_V2: str = "true"

        self.llm = Agent1.llm

        self.llm_with_tools = self.llm.bind_tools(get_tools())
        self.workflow = StateGraph(GraphState)
        # Adding nodes to the workflow
        self.workflow.add_node("chatbot", self.chatbot)
        self.workflow.add_node("tools", ToolNode(get_tools()))
        # TODO: Visualize these tools

        # Defining edges between nodes
        self.workflow.add_edge(START, "chatbot")
        self.workflow.add_edge("tools", "chatbot")
        self.workflow.add_edge("chatbot", END)
        
        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "chatbot",
            tools_condition
        )
        self.graph = self.workflow.compile()

        #with open("core/graph_node_network.png", 'wb') as f:
            #f.write(self.graph.get_graph().draw_mermaid_png())
    
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
        total_tokens = 0
        try:
            input = {"messages": [("human", user_prompt)]}
            async for event in self.graph.astream_events(input, version='v2'):
                event_type = event.get('event')

                # Passes over events that are start events
                if event_type == 'on_chain_start':
                    print("This event is on_chain_start")
                    continue

                # Returns the AI response 
                # //TODO Fix that it streams chuncks it rather than AIMessage
                if event_type == 'on_chain_end':
                    print(event['data'])
                    for message in event['data']['output']['messages']:
                        if isinstance(message, AIMessage):
                            data = message.content
                            socketio.emit("chunk", data)

                            if hasattr(message, 'usage_metadata'):
                                usage_metadata = message.usage_metadata
                                if usage_metadata:
                                    total_tokens = usage_metadata.get('total_tokens')
                                    socketio.emit("tokens", total_tokens)

    
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