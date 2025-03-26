from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from graph.node import *
from agents.WebSocketAgent import WebSocketAgent 

class CalendarSubGraph(WebSocketAgent):
    def __init__(self):
        self.workflow = StateGraph(GraphState)
        self.node = Node()

        self.workflow.add_node(START, self.node.calendar_decision_agent())
        self.workflow.add_node("calendar_tool", ToolNode(get_tools()))
        self.workflow.add_node("use_calendar_tool", self.node.calendar_tool_decider())


        self.workflow.add_edge(START, "calendar_tool")
        
        self.workflow.add_conditional_edges(
            "calendar_tool",
            self.node.calendar_router,
            {"use_calendar_tool": "use_calendar_tool", "return_to_jarvis": START}
        )
        self.work


        