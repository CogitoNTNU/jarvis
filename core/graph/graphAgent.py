print("graphAgent.py imported")  # Top of file

from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from graph.node import *
from time import sleep
from fastapi.websockets import WebSocket
from ai_agents.WebSocketAgent import WebSocketAgent 
from .subgraph.calendarSubGraph import CalendarSubGraph
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver() # Used to save state using checkpointing. See 'config' and astream execution furhter down.
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class Graph(WebSocketAgent):
    def __init__(self):
        log.info("Graph __init__ starting")
        try:
            
            print("""
------------------------------
Instantiated Graph Agent....
------------------------------  
            """)
            self.workflow = StateGraph(GraphState)
            self.node = Node()
            
            # Initialize to None first to avoid the AttributeError
            self.calendarSubgraph = None
            try:
                self.calendarSubgraph = CalendarSubGraph()
                print("CalendarSubGraph successfully initialized!")
            except Exception as e:
                print(f"Warning: Could not initialize CalendarSubGraph: {e}")

            # Inform the node if calendar is available
            self.node.calendar_available = self.calendarSubgraph is not None
            print(f"Calendar functionality available: {self.node.calendar_available}")

            # Basic nodes that are always available
            self.workflow.add_node("jarvis_agent", self.node.jarvis_agent)
            self.workflow.add_node("agent_decider", self.node.tool_agent_decider)
            self.workflow.add_node("generate", self.node.response_generator)
            self.workflow.add_node("tools", ToolNode(get_tools()))
            self.workflow.add_node("perplexity_agent", self.node.perplexity_agent)
            self.workflow.add_node("other_agent", self.node.other_agent)
            
            # Only add the calendar_node if the subgraph was successfully initialized
            if self.calendarSubgraph is not None:
                self.workflow.add_node("calendar_node", self.calendarSubgraph.calendar_subgraph)
                # Connect it to the graph
                self.workflow.add_edge("calendar_node", "jarvis_agent")
            else:
                print("Warning: Calendar functionality will not be available")
                
            self.workflow.add_edge(START, "jarvis_agent")
            self.workflow.add_edge("perplexity_agent", "tools")
            self.workflow.add_edge("other_agent", "tools")
            self.workflow.add_edge("tools", "jarvis_agent")
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
            
            # Conditionally include calendar in agent_router options
            router_options = {"perplexity": "perplexity_agent", "other": "other_agent"}
            if self.calendarSubgraph is not None:
                router_options["calendar"] = "calendar_node"
                print("Added 'calendar' to router options")
                
            self.workflow.add_conditional_edges(
                "agent_decider",
                self.node.agent_router,
                router_options
            )
            print(f"Final router options: {router_options}")
            
            self.graph = self.workflow.compile(checkpointer=memory) #Compiles the graph using memory checkpointer
            # try:
            #     with open("graph_node_network.png", 'wb') as f:
            #         f.write(self.graph.get_graph().draw_mermaid_png())
            # except Exception as e:
            #     print(f"Warning: Could not draw or save Mermaid diagram: {e}")
            log.info("Graph __init__ completed")
        except Exception as e:
            print(f"Exception in Graph __init__: {e}")
            log.info("Exception in Graph __init__")
            raise

    def chatbot(self, state: GraphState):
        """
        Simple bot that invokes the list of previous messages
        and returns the result which will be added to the list of messages.
        """
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Remove. This is just a placeholder
        for event in self.graph.stream({"messages": [HumanMessage(content=user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    # Keep the method for possible future use but don't add it as a node
    def process_calendar_event(self, state: GraphState):
        # Process calendar events that were added to state by the subgraph
        if state.get("data", {}).get("calendar_event"):
            calendar_event = state["data"]["calendar_event"]
            # Do something with the calendar event if needed
            print(f"Calendar event created: {calendar_event}")
        return state
