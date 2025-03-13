from typing_extensions import TypedDict
from fastapi.websockets import WebSocket
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessageChunk, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition
import main
"""
Baseclass for all agents using websocket and requires the simple .run function
"""
class WebSocketAgent:
    async def simple_run(self, user_prompt: str):
        try:
            input_data = {"messages": [("human", user_prompt)]}
            config = {"configurable": {"thread_id": "1"}}
            async for event in self.graph.astream_events(input_data, config, version='v2'):
                event_type = event.get('event')
                
                ### AI message end
                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]
                    return ai_message.content

        except Exception as e:
            print(f"Error in AI processing: {e}")
            return str(e)


    async def run(self, user_prompt: str, session_id: str):
        """
        Run the agent with a user prompt and send the response via FastAPI WebSockets.
        """
        config = {"configurable": {"thread_id": "1"}}
        websocket = main.active_websockets[session_id] # Gets correct websocket
        print("Getting websocket...")
        print(main.active_websockets)
        print(websocket)
        try:
            input_data = {"messages": [("human", user_prompt)]}
            await websocket.send_json({"event": "start_message", "data": " "})

            async for event in self.graph.astream_events(input_data, config, version='v2'):
                event_type = event.get('event')
                
                ### Tool response
                if event_type == 'on_chain_stream' and event['name'] == 'tools':
                    tool_response = event['data']['chunk']['messages'][-1]
                    if isinstance(tool_response, ToolMessage):
                        print(f"Tool Message: {tool_response.content}")
                        try:
                            await websocket.send_json({"event": "tool_message", "data": tool_response.content})
                        except Exception as e:
                            print(f"Error sending tool message: {e}")
                        continue

                ### AI message end
                if event_type == 'on_chain_end' and event['name'] == 'LangGraph':
                    ai_message = event['data']['output']['messages'][-1]

                    if isinstance(ai_message, AIMessage):
                        print(f"AI Message: {ai_message.content}")
                        try:
                            # Send AI message
                            await websocket.send_json({"event": "ai_message", "data": ai_message.content})
                        except Exception as e:
                            print(f"Error sending AI message: {e}")

                return ai_message.content
        except Exception as e:
            print(f"Error in AI processing: {e}")
            return str(e)