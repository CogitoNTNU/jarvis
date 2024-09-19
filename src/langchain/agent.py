from langchain_openai import ChatOpenAI
from src.langchain.graphstate import GraphState
from src.langchain.tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

class Agent:
    def __init__(self, model_type) -> None:
        self.llm = ChatOpenAI(
            model=model_type,
        )
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

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        #state_of_chatbot = self.llm_with_tools.invoke(state["messages"]).tool_calls
        #print("Tools called: " + state_of_chatbot["name"][-1].content)
        
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    
