from flask import Flask, request, url_for, jsonify
from graphAgent import Graph
from models import Model
from summarize_chat import summarize_chat
from rag import embed_and_store
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT
import asyncio  
from modules.user_data_setup import check_folders
from modules.chat import read_chat
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#
#   Setup
#
print("J is booting up....")
check_folders() # Check directories are made for user data
read_chat("1")

#
#   Server config
#
app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for WebSocket

# Agent instantiation
jarvis = Graph() # API key is configured in agent.py

#
#
#   HTTP(S) routes below
#
#
@app.route("/")
def hello_world():
    return app.send_static_file('index.html')

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
    emit("You're connected to Jarvis streaming server...")
    print('UI connected to backend')

# Base event that's fired when user gracefully disconnects
@socketio.on('disconnect')
def disconnect():
    print('UI disconnected')

# Custom event. Fired when the user sends a prompt.
@socketio.on('user_prompt')
def handle_prompt(data):
    try:
        conversation_id = data['conversation_id'] # grabs the conversation ID
        socketio.emit("start_message")
        asyncio.run(jarvis.run(data['prompt'], socketio), debug=True) # prompts Jarvis and hands off emitting to the graphAgent.
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f'Something very bad happened: {e}')
        return jsonify({"status": "error"})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=PORT, allow_unsafe_werkzeug=True)

# hello