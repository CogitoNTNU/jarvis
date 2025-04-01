from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from graph.node import *
from time import sleep
from fastapi.websockets import WebSocket
from ai_agents.WebSocketAgent import WebSocketAgent 
from subgraph.calenderSubGraph import CalendarSubGraph
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver() # Used to save state using checkpointing. See 'config' and astream execution furhter down.

class Graph(WebSocketAgent):
    def __init__(self):
        LANGCHAIN_TRACING_V2: str = "true"
        print("""
------------------------------
Instantiated Graph Agent....
------------------------------  
            """)
        self.workflow = StateGraph(GraphState)
        self.node = Node()
        self.calendar_subgraph = CalendarSubGraph()

        self.workflow.add_node("jarvis_agent", self.node.jarvis_agent)
        self.workflow.add_node("agent_decider", self.node.tool_agent_decider)
        self.workflow.add_node("generate", self.node.response_generator)
        self.workflow.add_node("tools", ToolNode(get_tools()))
        
        self.workflow.add_node("perplexity_agent", self.node.perplexity_agent)
        self.workflow.add_node("calendar_tool", ToolNode(get_tools()))
        self.workflow.add_node("calendar_node", self.calendar_subgraph)                            
        self.workflow.add_node("other_agent", self.node.other_agent)
        

        self.workflow.add_edge(START, "jarvis_agent")
        self.workflow.add_edge("perplexity_agent", "tools")
        self.workflow.add_edge("use_calendar_tool", "calendar_tool")
        self.workflow.add_edge("calendar_tool", "calendar_decider")
        self.workflow.add_edge("other_agent", "tools")
        self.workflow.add_edge("tools", "jarvis_agent")
        #self.workflow.add_edge("jarvis_agent", "generate")
        self.workflow.add_edge("generate", END)

        # Defining conditional edges
        self.workflow.add_conditional_edges(
            "jarvis_agent",
            self.node.router,
            {
                "generate": "generate",
                "use_tool": "agent_decider",
            }
        )
        
        self.workflow.add_conditional_edges(
            "agent_decider",
            self.node.agent_router,
            {"perplexity": "perplexity_agent", "calendar": "calendar_decider", "other": "other_agent"}
        )

        self.workflow.add_conditional_edges(
            "calendar_decider",
            self.node.calendar_router,
            {"use_calendar_tool": "use_calendar_tool", "return_to_jarvis": "jarvis_agent"}
        )

        self.graph = self.workflow.compile(checkpointer=memory) #Compiles the graph using memory checkpointer
        
        with open("graph_node_network.png", 'wb') as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Remove. This is just a placeholder
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
