from graph.graphstate import GraphState
from tools.tools import get_tools
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from graph.node import *
from time import sleep
from fastapi.websockets import WebSocket
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver() # Used to save state using checkpointing. See 'config' and astream execution furhter down.

class Graph:
    def __init__(self):
        LANGCHAIN_TRACING_V2: str = "true"
        print("""
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

    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}} # TODO: Remove. This is just a placeholder
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

    async def run(self, user_prompt: str, websocket: WebSocket):
        """
        Run the agent with a user prompt and send the response via FastAPI WebSockets.
        """
        config = {"configurable": {"thread_id": "1"}}

        try:
            input_data = {"messages": [("human", user_prompt)]}
            await websocket.send_json({"event": "start_message", "data": " "})

            async for event in self.graph.astream_events(input_data, config, version='v2'):
                event_type = event.get('event')

                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]

                    if isinstance(ai_message, AIMessage):
                        print(f"AI Message: {ai_message.content}")
                        # Handle tool calls
                        # if 'tool_calls' in ai_message.additional_kwargs:
                        #     try:
                        #         tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
                        #         await websocket.send_json({"event": "tool_call", "data": tool_call})
                        #         continue
                        #     except Exception as e:
                        #         print(f"Error processing tool call: {e}")
                        #         return str(e)

                        try:
                            # Send AI message
                            await websocket.send_json({"event": "ai_message", "data": ai_message.content})
                        except Exception as e:
                            print(f"Error sending AI message: {e}")

                        # try:
                        #     # Send token usage data
                        # except Exception as e:
                        #     print(f"Error sending token usage data: {e}")
                        # continue

                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]
                    print(f"Tool Response: {tool_response}")
                    if isinstance(tool_response, ToolMessage):
                        try:
                            await websocket.send_json({"event": "tool_message", "data": tool_response.content})
                        except Exception as e:
                            print(f"Error sending tool message: {e}")
                        continue

            return ai_message.content  # Send this to MongoDB
        except Exception as e:
            print(f"Error in AI processing: {e}")
            return str(e)
        



# UNFINISHED - legacy
    # def run_stream_only(self, user_prompt: str):
    #     """
    #     Run the agent, returning a token stream.
    #     """
    #     print('Running stream...')
    #     print(user_prompt)
    #     print(type(user_prompt))
    #     for chunk in self.llm.stream(user_prompt):
    #         yield chunk.content

    # async def run(self, user_prompt: str, socketio):
    #     """
    #     Run the agent with a user prompt and emit the response and total tokens via socket
    #     """
    #     try:
    #         input = {"messages": [("human", user_prompt)]}
    #         socketio.emit("start_message", " ")
    #         config = {"configurable": {"thread_id": "1"}} # Thread here is hardcoded for now.
    #         async for event in self.graph.astream_events(input, config, version='v2'): # The config uses the memory checkpoint to save chat state. Only in-memory, not persistent yet.
    #             event_type = event.get('event')
    #             # Focuses only on the 'on_chain_stream'-events. 
    #             # There may be better events to base the response on
    #             if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
    #                 ai_message = event['data']['output']['messages'][-1]

    #                 if isinstance(ai_message, AIMessage):
    #                     print(ai_message)
    #                     if 'tool_calls' in ai_message.additional_kwargs:
    #                         try: 
    #                             tool_call = ai_message.additional_kwargs['tool_calls'][0]['function']
    #                             #tool_call_id = ai_message.additional_kwargs['call_tool'][0]['tool_call_id']
    #                             socketio.emit("tool_call", tool_call)
    #                             continue
    #                         except Exception as e:
    #                             return e
                    
    #                     socketio.emit("chunk", ai_message.content) # Emits the entire message over the websocket event "chunk"
    #                     # TODO: POST REQUEST TO TTS
    #                     socketio.emit("tokens", ai_message.usage_metadata['total_tokens'])
    #                     continue
                
    #             if event_type == 'on_chain_stream' and event['name'] == 'tools':
    #                 tool_response = event['data']['chunk']['messages'][-1]
    #                 if isinstance(tool_response, ToolMessage):
    #                     socketio.emit("tool_response", tool_response.content)
    #                     continue

    #         return "success"
    #     except Exception as e:
    #         print(e)
    #         return e
        
