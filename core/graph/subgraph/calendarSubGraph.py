from graph.graphstate import GraphState, CalendarGraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from graph.node import *
from ai_agents.WebSocketAgent import WebSocketAgent
from langgraph.checkpoint.memory import MemorySaver
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

memory = MemorySaver()

class CalendarSubGraph(WebSocketAgent):
    def __init__(self):
        log.info("Initializing CalendarSubGraph workflow...")
        self.workflow = StateGraph(CalendarGraphState)
        self.node = Node()

        self.workflow.add_node("calendar", self.node.calendar_decision_agent)
        self.workflow.add_node("calendar_tool", ToolNode(calendar_based_tools()))
        self.workflow.add_node("use_calendar_tool", self.node.calendar_tool_decider)
        
        
        # Add a node to handle calendar events that will be passed back to the parent graph
        self.workflow.add_node("process_calendar_event", self.handle_calendar_event)
        

        log.info("Setting up graph structure and workflow...")
        # The graph structure already supports looping for multiple calendar events:
        # 1. START begins at the calendar node
        # 2. When we use a tool, we go to calendar_tool
        # 3. After using the tool, we loop back to calendar for further decisions
        # 4. This cycle continues until we decide to return to Jarvis
        self.workflow.add_edge(START, "calendar")
        self.workflow.add_edge("use_calendar_tool", "calendar_tool")
        self.workflow.add_edge("calendar_tool", "calendar")  # This creates the loop for multiple events
        log.debug("Added edge: calendar_tool -> calendar")
        log.debug(f"Added edge: process_calendar_event -> {END}")
        
        log.info("Adding conditional edges for decision routing...")
        self.workflow.add_conditional_edges(
            "calendar",
            self.node.calendar_router,
            {"use_calendar_tool": "use_calendar_tool", "return_to_jarvis": "process_calendar_event"}
        )
        log.debug("Added conditional edges from calendar node")
        
        # Using a simpler compile approach without input/output mapping
        # since the version doesn't support those parameters
        self.calendar_subgraph = self.workflow.compile(checkpointer=memory)
        log.info("Successfully compiled CalendarSubGraph workflow")

        try:
            with open("calendar_subgraph.png", 'wb') as f:
                f.write(self.calendar_subgraph.get_graph().draw_mermaid_png())
            log.info("Successfully saved calendar subgraph visualization to calendar_subgraph.png")
        except Exception as e:
            log.warning(f"Could not generate calendar_subgraph.png: {e}")
            log.debug(f"Visualization error details: {str(e)}", exc_info=True)
    
    def handle_calendar_event(self, state: CalendarGraphState):
        """
        This node prepares data to be passed back to the parent graph.
        It collects all calendar events created during this subgraph execution.
        """
        # Initialize calendar_events if not already present
        if "calendar_events" not in state:
            state["calendar_events"] = {}
        
        # If there's a new calendar event from a tool, add it to our collection
        if state.get("calendar_data") and isinstance(state["calendar_data"], dict):
            # Extract event data from calendar_data
            for key, event_info in state["calendar_data"].items():
                if isinstance(event_info, dict) and "event_id" in event_info:
                    event_id = event_info["event_id"]
                    # Store event using its ID as key to prevent duplicates
                    if event_id not in state["calendar_events"]:
                        state["calendar_events"][event_id] = event_info
                        # Add a confirmation message
                        state["messages"].append({
                            "role": "system",
                            "content": f"Calendar event stored: {event_info.get('summary', 'Unnamed event')}"
                        })
        
        # Summarize all created events before returning to main graph
        if state.get("calendar_events"):
            events = state["calendar_events"]
            num_events = len(events)
            state["messages"].append({
                "role": "system",
                "content": f"{num_events} calendar event(s) ready to transfer to main system."
            })
        
        return state

    def transfer_events_to_main_graph(self, main_state: GraphState, calendar_state: CalendarGraphState):
        """
        Transfer calendar events from the subgraph state to the main graph state.
        Called after the calendar subgraph completes execution.
        """
        # Initialize calendar_events in main state if needed
        if "calendar_events" not in main_state:
            main_state["calendar_events"] = {}
        
        # Transfer events from calendar subgraph to main graph
        if calendar_state.get("calendar_events"):
            for event_id, event_info in calendar_state["calendar_events"].items():
                main_state["calendar_events"][event_id] = event_info
            
            # Also add event data to the main data store for agents to access
            if "data" not in main_state:
                main_state["data"] = {}
            if "calendar" not in main_state["data"]:
                main_state["data"]["calendar"] = {}
            
            main_state["data"]["calendar"]["events"] = main_state["calendar_events"]
            
        return main_state
