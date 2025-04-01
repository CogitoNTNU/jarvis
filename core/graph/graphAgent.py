from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from graph.node import *
from time import sleep
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver() # Used to save state using checkpointing. See 'config' and astream execution furhter down.

from modules.logging_utils import logger

class Graph:
    def __init__(self):
        LANGCHAIN_TRACING_V2: str = "true"
        logger.info("""
------------------------------
Instantiated Graph Agent....
------------------------------  
            """)
        self.workflow = StateGraph(GraphState)
        self.node = Node()

        self.workflow.add_node("jarvis_agent", self.node.jarvis_agent)
        self.workflow.add_node("agent_decider", self.node.tool_agent_decider)
        self.workflow.add_node("generate", self.node.response_generator)
        self.workflow.add_node("tools", ToolNode(get_tools()))
        
        self.workflow.add_node("perplexity_agent", self.node.perplexity_agent)
        self.workflow.add_node("calendar_tool", ToolNode(get_tools()))
        self.workflow.add_node("use_calendar_tool", self.node.calendar_tool_decider)
        self.workflow.add_node("calendar_decider", self.node.calendar_decision_agent)
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
            {"generate": "generate", "use_tool": "agent_decider"}
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

# UNFINISHED
    def run_stream_only(self, user_prompt: str):
        """
        Run the agent, returning a token stream.
        """
        logger.info('Running stream...')
        logger.info(user_prompt)
        logger.info(type(user_prompt))
        for chunk in self.llm.stream(user_prompt):
            yield chunk.content

    async def run(self, user_prompt: str, socketio):
        """
        Run the agent with a user prompt and emit the response and total tokens via socket
        """
        try:
            input = {"messages": [("human", user_prompt)]}
            socketio.emit("start_message", " ")
            config = {"configurable": {"thread_id": "1"}} # Thread here is hardcoded for now.
            async for event in self.graph.astream_events(input, config, version='v2'): # The config uses the memory checkpoint to save chat state. Only in-memory, not persistent yet.
                event_type = event.get('event')
                # Focuses only on the 'on_chain_stream'-events. 
                # There may be better events to base the response on
                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]

                    if isinstance(ai_message, AIMessage):
                        logger.info(ai_message)
                        if 'tool_calls' in ai_message.additional_kwargs:
                            try: 
                                tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
                                #tool_call_id = ai_message.additional_kwargs['call_tool'][0]['tool_call_id']
                                socketio.emit("tool_call", tool_call)
                                continue
                            except Exception as e:
                                return e
                    
                        socketio.emit("chunk", ai_message.content) # Emits the entire message over the websocket event "chunk"
                        # TODO: POST REQUEST TO TTS
                        socketio.emit("tokens", ai_message.usage_metadata['total_tokens'])
                        continue
                
                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]
                    if isinstance(tool_response, ToolMessage):
                        socketio.emit("tool_response", tool_response.content)
                        continue

            return "success"
        except Exception as e:
            logger.info(e)
            return e
        
