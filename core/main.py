from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import pymongo
import requests
import logging
from collections import defaultdict

from graph.graphAgent import Graph
from agents.neo_agent_mistral_small import NeoAgentLlama
from agents.neo_agent_openai import NeoAgent
from summarize_chat import summarize_chat
from rag import embed_and_store
from config import PORT
from modules.user_data_setup import check_folders
from modules.chat import read_chat

log = logging.getLogger("uvicorn")
log.setLevel(logging.ERROR)

'''
    FOR API DOCUMENTATION, VISIT: http://localhost:3000/docs
    
    Websockets are not automatically documented.

    Running using uvicorn outside of docker: 
    1. Enter a venv
    2. python -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload
'''

#
# Setup
#
print("Booting....")
check_folders()  # Check directories are made for user data

#
# Server config
#
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Make CORS more restrictive
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent instantiation
jarvis = NeoAgent()  
#jarvis = NeoAgentLlama()

# Initialize active_chats with standard llm format
active_chats: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: {"chat_history": []})

# MongoDB Connection
client = pymongo.MongoClient("mongodb://mongodb:27017/")
db = client["chat_database"]
collection = db["chats"]

# WebSocket manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"Session {session_id} connected.")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        print(f"Session {session_id} disconnected.")

    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

ws_manager = WebSocketManager()

#
# HTTP Endpoints
#
@app.get("/")
async def hello_world():
    return FileResponse("static/index.html")

@app.get("/ping_server")
async def ping_server():
    return "Hello from Jarvis API!"

# Pydantic models for request/response bodies
class ChatSummaryRequest(BaseModel):
    chat_history: List[Dict[str, str]]
    user_id: str

@app.post("/vectorize_chat")
async def summarize_store(data: ChatSummaryRequest):
    if not data.chat_history or not data.user_id:
        raise HTTPException(status_code=400, detail="chat_history and user_id are required")

    summary = summarize_chat(data.chat_history)
    embed_and_store(summary, data.user_id)

    return {"status": "success", "summary": summary}

class RecordingRequest(BaseModel):
    conversation_id: str

@app.post("/start_recording")
async def start_recording_route(data: RecordingRequest):
    print("Starting recording...")
    response = requests.post(f"http://speech-to-text:3001/start_recording/{data.conversation_id}")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to start recording")

    return {"status": "recording_started"}

@app.post("/recording_completed")
async def recording_completed(data: dict):
    text = data.get("text", "")
    conversation_id = data.get("conversation_id", "")
    print(f"Recording completed for conversation ID {conversation_id} with text: {text}")

    asyncio.create_task(jarvis.run(text))  # Run Jarvis response asynchronously

    return {"status": "success"}

#
# WebSocket Endpoints
#

class UserPromptRequest(BaseModel):
    event: str
    conversation_id: str
    prompt: str

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)

    try:
        while True:
            data = await websocket.receive_json()
            validated_data = UserPromptRequest(**data) # Unpacks data into UserPromptRequest
            event_type = data.get("event")

            ### User prompt
            if event_type == "user_prompt": 
                conversation_id = data.get("conversation_id")
                prompt = data.get("prompt")

                chat_entry = {
                    "session_id": session_id,
                    "conversation_id": conversation_id,
                    "human_message": prompt,
                    "ai_message": "",  # Will be updated later
                }

                inserted_id = collection.insert_one(chat_entry).inserted_id
                print(f"Chat entry inserted with ID: {inserted_id}")

                await ws_manager.send_message(session_id, "start_message")

                async def run_and_store():
                    response = await jarvis.run(prompt)
                    collection.update_one(
                        {"_id": inserted_id},
                        {"$set": {"ai_message": response}}
                    )
                    print(f"Updated MongoDB entry {inserted_id} with AI response")

                    if session_id in active_chats:
                        active_chats[session_id]["chat_history"].append(chat_entry)

                    await ws_manager.send_message(session_id, response)
                try:
                    asyncio.create_task(run_and_store()) ### Non blocking call to run_and_store
                except Exception as e:
                    print(f"Jarvis encountered an error responding to user prompt: {e}")

            ### Start recording
            elif event_type == "start_recording":
                print("Starting recording via socket...")
                response = requests.post(f"http://speech-to-text:3001/start_recording/{conversation_id}")

                if response.status_code != 200:
                    await ws_manager.send_message(session_id, '{"status": "error", "text": "Failed to start recording"}')
                    return

                await ws_manager.send_message(session_id, '{"status": "recording_started"}')

            ### Get chat history
            elif event_type == "get_chat_history":
                history = active_chats.get(session_id, {"chat_history": []})
                await ws_manager.send_message(session_id, str(history))

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)

#
# Server Startup
#
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
