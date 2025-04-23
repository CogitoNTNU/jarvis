from graph.graphstate import GraphState, CalendarGraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from graph.node import *
from ai_agents.WebSocketAgent import WebSocketAgent
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()

class CalendarSubGraph(WebSocketAgent):
    def __init__(self):
        self.workflow = StateGraph(CalendarGraphState)
        self.node = Node()

        self.workflow.add_node("calendar", self.node.calendar_decision_agent)
        self.workflow.add_node("calendar_tool", ToolNode(calendar_based_tools()))
        self.workflow.add_node("use_calendar_tool", self.node.calendar_tool_decider)
        
        # Add a node to handle calendar events that will be passed back to the parent graph
        self.workflow.add_node("process_calendar_event", self.handle_calendar_event)

        # The graph structure already supports looping for multiple calendar events:
        # 1. START begins at the calendar node
        # 2. When we use a tool, we go to calendar_tool
        # 3. After using the tool, we loop back to calendar for further decisions
        # 4. This cycle continues until we decide to return to Jarvis
        self.workflow.add_edge(START, "calendar")
        self.workflow.add_edge("use_calendar_tool", "calendar_tool")
        self.workflow.add_edge("calendar_tool", "calendar")  # This creates the loop for multiple events
        self.workflow.add_edge("process_calendar_event", END)
        
        self.workflow.add_conditional_edges(
            "calendar",
            self.node.calendar_router,
            {"use_calendar_tool": "use_calendar_tool", "return_to_jarvis": "process_calendar_event"}
        )
        
        # Using a simpler compile approach without input/output mapping
        # since the version doesn't support those parameters
        self.calendar_subgraph = self.workflow.compile(checkpointer=memory)

        # try:
        #     with open("calendar_subgraph.png", 'wb') as f:
        #         f.write(self.calendar_subgraph.get_graph().draw_mermaid_png())
        # except Exception as e:
        #     print(f"Warning: Could not generate calendar_subgraph.png: {e}")
    
    def handle_calendar_event(self, state: CalendarGraphState):
        """
        This node prepares data to be passed back to the parent graph.
        It collects all calendar events created during this subgraph execution.
        """
        # Check if we've already started collecting events
        if not state.get("all_calendar_events"):
            state["all_calendar_events"] = []
        
        # If there's a new calendar event, add it to our collection
        if state.get("calendar_event"):
            event_info = state["calendar_event"]
            state["all_calendar_events"].append(event_info)
            
            # Add a confirmation message
            state["messages"].append({
                "role": "system",
                "content": f"Calendar event created: {event_info}"
            })
        
        # Summarize all created events before returning to main graph
        if state.get("all_calendar_events"):
            events = state["all_calendar_events"]
            num_events = len(events)
            state["messages"].append({
                "role": "system",
                "content": f"Created {num_events} calendar event(s) in this session."
            })
        
        return state
