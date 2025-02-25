from flask import Flask, request, url_for, jsonify
from graphAgent import Graph
from Agents.neo_agent_mistral_small import NeoAgentLlama
from Agents.neo_agent_openai import NeoAgent
from models import Model
from summarize_chat import summarize_chat
from rag import embed_and_store
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT
import asyncio  
from modules.user_data_setup import check_folders
from modules.chat import read_chat
import requests
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
from collections import defaultdict

import pymongo

#
#   Setup
#
print("Jarvis is booting up....")
check_folders() # Check directories are made for user data

#
#   Server config
#
app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for WebSocket

# Agent instantiation
# Graph() contains all complex tools
# NeoAgent() is a simple ReAct agent that only has websearch and the add tool. For testing purposes.
#jarvis = Graph() # API key is configured in agent.py
jarvis = NeoAgent() #NeoAgentLlama() #

# Initialize active_chatss with the correct format
active_chats = defaultdict(lambda: {"chat_history": []})

#
#
#   HTTP(S) routes below
#
#
@app.route("/")
def hello_world():
    return app.send_static_file('index.html')

# Route to get metadata like name, id, descriptions of all user chats
@app.route("/chats/metadata")
def get_chats():
    return "lmao" # Why does this return lmao?

@app.route('/vectorize_chat', methods=['POST'])
def summarize_store():
    data = request.json
    chat_history = data.get('chat_history')
    user_id = data.get('user_id')

    if not chat_history or not user_id:
        return {"error": "chat_history and user_id are required"}, 400

    summary = summarize_chat(chat_history)
    embed_and_store(summary, user_id)

    return {"status": "success", "summary": summary}

#
#
#   Socket.IO events below
#
#
# Base event that's fired when a user connects
@socketio.on('connect') 
def connect(data):
    session_id = request.sid
    emit("You're connected to Jarvis streaming server...")
    print('UI connected to backend')
    print(f'Session ID: {session_id}')

# Base event that's fired when user gracefully disconnects
@socketio.on('disconnect')
def disconnect():
    session_id = request.sid
    if session_id in active_chats:
        # Get the chat history before deleting it
        chat_history = active_chats[session_id]
        
        try:
            # Call summarize_chat directly instead of the route handler
            summary = summarize_chat(chat_history)
            # Then call embed_and_store directly
            embed_and_store(summary, "1")  # Using dummy user_id "1"
            print(f'Chat history summarized and stored')
        except Exception as e:
            print(f'Error summarizing chat history: {e}')
        
        # Clean up the chat history
        del active_chats[session_id]
    
    print('UI disconnected')
    print(f'Session ID: {session_id}')



client = pymongo.MongoClient("mongodb://absolute-mongo:27017/") #jeg tror denne lenken er kaputt #("mongodb://localhost:27017/") #
db = client["chat_database"]
collection = db["chats"] 

# Custom event. Fired when the user sends a prompt.
@socketio.on('user_prompt')
def handle_prompt(data):
    try:
        session_id = request.sid
        conversation_id = data['conversation_id'] # unused for now
        
        # Create new chat entry with human message
        # chat_entry = {
        #     "human_message": data['prompt'],
        #     "ai_message": ""  # Will be filled when AI responds
        # }
        chat_entry = {
            "session_id": session_id,
            "conversation_id": conversation_id,
            "human_message": data['prompt'],
            "ai_message": "",  # Will be updated later
        }
        # Insert chat entry into MongoDB
        inserted_id = collection.insert_one(chat_entry).inserted_id
        print(f"Chat entry inserted with ID: {inserted_id}")


        socketio.emit("start_message")
        
        # Run the AI response
        async def run_and_store():
            response = await jarvis.run(data['prompt'], socketio)
            ### TODO: Replace this with GraphState for chat history.
            collection.update_one(
                {"_id": inserted_id},
                {"$set": {"ai_message": response}}
            )

            print(f"Updated MongoDB entry {inserted_id} with AI response")

            # Optional: Store in memory (if used elsewhere)
            if session_id in active_chats:
                active_chats[session_id]["chat_history"].append(chat_entry)
            # Update the AI response in the chat entry
            # chat_entry["ai_message"] = response
            # # Add completed chat entry to history
            # active_chats[session_id]["chat_history"].append(chat_entry)
            
        asyncio.run(run_and_store(), debug=True)
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f'Something very bad happened: {e}')
        return jsonify({"status": "error"})

# Custom event. Fired when the user click the button with the cute little microphone icon.
@app.route('/start_recording', methods=['POST'])
def start_recording_route():
    data = request.json
    conversation_id = data.get('conversation_id')

    print("Starting recording...")

    # Send POST request to the recorder to start recording
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f'http://speech-to-text:3001/start_recording/{conversation_id}', headers=headers, json=data)
        
    if response.status_code != 200:
        return jsonify({"status": "error", "text": "Failed to start recording"}), 500

    return jsonify({"status": "recording_started"}), 200


@socketio.on('start_recording')
def start_recording_socket(data):
    # This function handles the socket event to start recording
    conversation_id = data.get('conversation_id')

    print("Starting recording via socket...")

    # Send POST request to the recorder to start recording
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f'http://speech-to-text:3001/start_recording/{conversation_id}', headers=headers, json=data)

    if response.status_code != 200:
        socketio.emit('recording_failed', {"status": "error", "text": "Failed to start recording"})
        return

    socketio.emit('recording_started', {"status": "recording_started"})

@app.route('/recording_completed', methods=['POST'])
def recording_completed():
    data = request.json
    text = data.get('text', '')
    socketio.emit("recording", text)

    conversation_id = data.get('conversation_id', '')
    print(f"Recording completed for conversation ID {conversation_id} with text:", text)
    
    # Process the recorded text as needed (e.g., send to Jarvis or other services)
    asyncio.run(jarvis.run(text, socketio))  # Assuming jarvis.run is asynchronous

    return jsonify({"status": "success"}), 200


@socketio.on('get_chat_history')
def get_chat_history():
    session_id = request.sid
    if session_id in active_chats:
        return active_chats[session_id]
    return {"chat_history": []}

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True) # Hardcoded port, same as docker compose and dockerfile

# hello
# TODO say hello back to whoever wrote this