from langchain_openai import ChatOpenAI
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from tools.tools import get_tools
from graphstate import GraphState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage
from IPython.display import Image, display

import json
import os
import langchain
langchain.verbose = False
#sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class JarvisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
        )
        self.chat_history_path: str = "./chat_history.json"
        self.base_prompt = [("system", "You are a helpful personal assistant that helps the user with all their tasks and requests.")]

        self.llm_with_tools = self.llm.bind_tools(get_tools())
        
        self.workflow = StateGraph(GraphState)

        # Adding nodes to the workflow
        self.workflow.add_node("chatbot", self.chatbot)
        self.workflow.add_node("tools", ToolNode(get_tools()))

        # Defining edges between nodes
        self.workflow.add_edge(START, "chatbot")
        self.workflow.add_edge("tools", "chatbot")

        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "chatbot",
            tools_condition
        )

        self.graph = self.workflow.compile()

        display(Image(self.graph.get_graph().draw_mermaid_png()))


    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        #state_of_chatbot = self.llm_with_tools.invoke(state["messages"]).tool_calls
        #print("Tools called: " + state_of_chatbot["name"][-1].content)
        
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}
    

    def __getGraph__(self):
        return self.graph

    def run(self, prompt: str):
        """
        A function that prompts the language model the given string and prints the response.
        """
        # messages = [("system", self.base_prompt + " This is their requst: " + prompt),
                    # ]
        # ai_msg = self.llm.invoke(messages)
        ai_msg = self.llm.invoke({"input": "{prompt}", "chat_history": self.read_chat_history()})

        self.save_chat_history(prompt, ai_msg.content)
        print(ai_msg.content)

    def read_chat_history(self) -> None:
        with open(self.chat_history_path, "r") as f:
            content = json.load(f)
            data = content["chat_history"]
            history = []
            for entry in data:
                history.append(HumanMessage(entry["Human"]))
                history.append(AIMessage(entry["AI"]))
            return history

    def save_chat_history(self, Humanmessage, AImessage) -> None:
        with open(self.chat_history_path, "r") as f:
            content = json.load(f)
            data = content["chat_history"]
            new_entry = {"Human": Humanmessage, "AI": AImessage}
            data.append(new_entry)
        with open(self.chat_history_path, "w") as f:
            json.dump(content, f)

#agent.run("Can you help me with my homework?")
# agent.read_chat_history()
# agent.save_chat_history("Can you help me with my homework?", "Sure, what do you need help with?")
# agent.read_chat_history()

if __name__ == "__main__":
    agent = JarvisAgent()
    user_input = input("User: ")
    for event in agent.__getGraph__().stream({"messages": [("user", user_input)]}):
        for value in event.values():
            if isinstance(value["messages"][-1], BaseMessage):
                print("Assistant:", value["messages"][-1].content) 



    
        
    


#agent = JarvisAgent()
# agent.run("Can you help me with my homework?")
# agent.run("What did I say in the previous prompt?")
# agent.read_chat_history()


# messages = [
#     (
#         "system",
#         "You are a helpful personal assistant that helps the user with all their tasks and requests.",
#     ),
# ]
# ai_msg = llm.invoke(messages)
# print(ai_msg.content)