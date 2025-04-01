from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from graph.node import *
from ai_agents.WebSocketAgent import WebSocketAgent
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()

class CalendarSubGraph(WebSocketAgent):
    def __init__(self):
        self.workflow = StateGraph(GraphState)
        self.node = Node()

        self.workflow.add_node("calendar", self.node.calendar_decision_agent())
        self.workflow.add_node("calendar_tool", ToolNode(get_tools()))
        self.workflow.add_node("use_calendar_tool", self.node.calendar_tool_decider())


        self.workflow.add_edge(START, "calendar")
        
        self.workflow.add_conditional_edges(
            "use_calendar_tool",
            "return_to_jarvis",
            self.node.calendar_router,
            {"use_calendar_tool": "use_calendar_tool", "return_to_jarvis": END}
        )

        
        
        self.calendar_subgraph = self.workflow.compile(checkpointer=memory)

        with open("calendar_subgraph.png", 'wb') as f:
            f.write(self.calendar_subgraph.get_graph().draw_mermaid_png())
        