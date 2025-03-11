from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import pymongo
import requests
import logging
from collections import defaultdict
import json

from graph.graphAgent import Graph
import agents.neo_agent_llama
from agents.neo_think_agent import NeoThinkAgent
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

# Mount static folder for UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Agent instantiation
jarvis = NeoThinkAgent()
#jarvis = NeoAgentLlama()

welcome_text = '''
     ____   _____  _____________   ____ ___  _________ 
    |    | /  _  \ \______  \   \ /   /|   |/   _____/ 
    |    |/  /_\  \|       _/\   Y   / |   |\_____  \  
/\__|    /    |    \    |   \ \     /  |   |/        \ 
\________\____|__  /____|_  /  \___/   |___/_______  / 
                 \/       \/                       \/  '''
print(welcome_text)

# Initialize active_chats with standard llm format
active_chats: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: {"chat_history": []})

# MongoDB Connection
client = None
collection = None  # Default to None if MongoDB isn't available

try:
    client = pymongo.MongoClient("mongodb://mongodb:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()  # Try to connect
    print("✅ Connected to MongoDB!")
    
    db = client["chat_database"]
    collection = db["chats"]
except pymongo.errors.ServerSelectionTimeoutError:
    print("❌ MongoDB is not available. Running without database features.")
    client = None  # Ensure client is None to prevent errors
    collection = None  # Prevent further crashes


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
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

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
    jarvis.run("prompt")
    session_id = data.get("session_id", "")
    text = data.get("text", "")
    conversation_id = data.get("conversation_id", "")
    print(f"Recording completed for conversation ID {conversation_id} with text: {text}")

    asyncio.create_task(jarvis.run(text), active_websockets[session_id])  # Run Jarvis response asynchronously

    return {"status": "success"}

#
# WebSocket Endpoints
#

# User prompting request models
class UserPromptData(BaseModel):
    prompt: str
    conversation_id: str

class UserPromptRequest(BaseModel):
    event: str
    data: UserPromptData

# Generic event request
class BaseEventRequest(BaseModel):
    event: str

def print_status(active_websocket):
    print("WebSocketAgent loaded...")
    print(active_websocket)

active_websockets = {}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)
    global active_websockets
    active_websockets[session_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("event")
            print(f"Received event: {event_type}")
            ### User prompt
            if event_type == "user_prompt":
                req = UserPromptRequest(**data) # Unpacks message into UserPromptRequest
                ai_response = await jarvis.run(req.data.prompt) # Run Jarvis response

            ### Get chat history
            elif event_type == "get_chat_history":
                history = active_chats.get(session_id, {"chat_history": []})
                await ws_manager.send_message(session_id, json.dumps(history))

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)

#
# Server Startup
#
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)


                    # if collection is None:  # Prevent MongoDB crash
                    #     print("MongoDB is not available. Skipping DB insert.")
                    # else:
                    #     chat_entry = {
                    #         "session_id": session_id,
                    #         "conversation_id": message.get("conversation_id", ""),
                    #         "human_message": message.get("prompt", ""),
                    #         "ai_message": "",
                    #     }
                    #     inserted_id = collection.insert_one(chat_entry).inserted_id
                    #     print(f"Chat entry inserted with ID: {inserted_id}")

                    #await ws_manager.send_message(session_id, response) # Send response to frontend
                    #print(f"Jarvis response sent to session {session_id}")
                    # local chat history storage/cache
                    # TODO: Make this purely mongoDB
                    # if session_id in active_chats:
                    #     active_chats[session_id]["chat_history"].append(chat_entry)

                    # try:
                    #     collection.update_one(
                    #         {"_id": inserted_id},
                    #         {"$set": {"ai_message": response}}
                    #     )
                    #     print(f"Updated MongoDB entry {inserted_id} with AI response")
                    # except Exception as e:
                    #     print(f"Jarvis encountered an error updating MongoDB entry: {e}")