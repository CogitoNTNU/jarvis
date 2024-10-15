from flask import Flask, request, url_for, jsonify
from graph import Graph
from models import Model
from summarize_chat import summarize_chat
from rag import embed_and_store
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT
import asyncio  

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
#s
#
@app.route("/")
def hello_world():
    return app.send_static_file('index.html')
    
@app.route('/send_message', methods=['POST', 'GET'])
def llm_request():
    if(request.method == 'POST'):
        data = request.json
        ai_message = jarvis.run(data['prompt'])
        return {"message": ai_message}

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
    print('Client connected')

# Base event that's fired when user gracefully disconnects
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')

# Custom event. Fired when the user sends a prompt.
@socketio.on('user_prompt')
def handle_prompt(data):
    print("huh")
    try:
        conversation_id = data['conversation_id'] # grabs the conversation ID
        socketio.emit("start_message")
        stream, tokens = jarvis.run(data['prompt']) # prompts Jarvis
        #stream = jarvis.run_stream_only(data['prompt'])
        chunk = ""
        for char in stream:
            if len(chunk) > 4:
                socketio.emit("chunk", chunk)
                chunk = char
            else:
                chunk += char
        #asyncio.sleep(500)
        socketio.emit("chunk", chunk)
        socketio.emit("tokens", tokens)
            
        return jsonify({"status": "success"})
    except Exception as e:
        print(f'Something very bad happened: {e}')
        return jsonify({"status": "error"})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=PORT, allow_unsafe_werkzeug=True)