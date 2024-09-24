from langchain_openai import ChatOpenAI
from graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage
from models import Model
import json
from config import OPENAI_API_KEY

class Agent:
    def __init__(self, model_type) -> None:
        #Langsmith Tracing
        LANGCHAIN_TRACING_V2: str = "true"

        self.llm = ChatOpenAI(
            model=model_type,
            temperature=0,
            max_tokens=512,
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

        #Saving image of graph node comment in and out as needed
        #with open("core/graph_node_network.png", 'wb') as f:
        #    f.write(self.graph.get_graph().draw_mermaid_png())

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        #state_of_chatbot = self.llm_with_tools.invoke(state["messages"]).tool_calls
        #print("Tools called: " + state_of_chatbot["name"][-1].content)
        
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
    async def run(self, user_prompt: str):
        """
        Run the agent with a user prompt and return the output.
        """
        first = True
        async for event in self.graph.stream({"messages": [("user", user_prompt)]}):
            print(event)
            for value in event.values():
                messages = value["messages"][-1]
                gathered = ""
                # if messages.content and not isinstance(messages, HumanMessage):
                #     print(messages.content, end="|", flush=True)

                if isinstance(messages, AIMessageChunk):
                    if first:
                        gathered = messages
                        first = False
                    else:
                        gathered += messages

                if isinstance(messages, BaseMessage):
                    total_tokens = messages.usage_metadata.get('total_tokens', 0)
                    #messages = messages.content
                    print(gathered)

                    return f"Assistant:", messages.content, gathered, total_tokens, f"Total tokens used {total_tokens}"
                
    #for testing in terminal
    """ def run(self, user_prompt: str):
        for event in self.graph.stream({"messages": [("user", user_prompt)]}):
            for value in event.values():
                if isinstance(value["messages"][-1], BaseMessage):
                    print("Assistant:", value["messages"][-1].content)

if __name__ == "__main__":
    agent = Agent("gpt-4o-mini")
    while True:
        user_prompt = input("User: ")
        agent.run(user_prompt) """
    
# Counting tokens: https://python.langchain.com/docs/how_to/llm_token_usage_tracking/
