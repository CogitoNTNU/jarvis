from langchain_openai import ChatOpenAI
from graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage

import os
import json
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Agent:
    def __init__(self, model_type) -> None:
        self.llm = ChatOpenAI(
            model=model_type,
            temperature=0,
        )

        self.llm_with_tools = self.llm.bind_tools(get_tools())
        
        self.workflow = StateGraph(GraphState)

        # Adding nodes to the workflow
        self.workflow.add_node("chatbot", self.chatbot)
        self.workflow.add_node("tools", ToolNode(get_tools()))
        # TODO: Visualize these tools

        # Defining edges between nodes
        self.workflow.add_edge(START, "chatbot")
        self.workflow.add_edge("tools", "chatbot")

        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "chatbot",
            tools_condition
        )

        self.graph = self.workflow.compile() # Compiles the workflow in a graph.

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        #state_of_chatbot = self.llm_with_tools.invoke(state["messages"]).tool_calls
        #print("Tools called: " + state_of_chatbot["name"][-1].content)
        
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}


# UNFINISHED
    def run_stream(self, user_prompt: str):
        """
        Run the agent, returning a token stream.
        """
        print('Running stream...')
        print(user_prompt)
        print(type(user_prompt))
        for chunk in self.llm.stream(user_prompt):
            yield chunk.content

    
    def run(self, user_prompt: str):
        """
        Run the agent with a user prompt and return the output.
        """
        for event in self.graph.stream({"messages": [("user", user_prompt)]}):
            for value in event.values():
                if isinstance(value["messages"][-1], BaseMessage):
                    return f"Assistant:", value["messages"][-1].content

    
# Counting tokens: https://python.langchain.com/docs/how_to/llm_token_usage_tracking/