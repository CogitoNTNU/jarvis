from flask import Flask, request, url_for
from agent import Agent
from models import Model
from summarize_chat import summarize_chat
from rag import embed_and_store
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS

#
#   Server config
#
app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for WebSocket

# Agent instantiation
jarvis = Agent(Model.gpt_4o) # API key is configured in agent.py

#
#
#   HTTP(S) routes below
#
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

@socketio.on('connect')
def connect(data):
    emit("You're connected to Jarvis streaming server...")
    print('Client connected')

@socketio.event
def disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    print(data['data'])

@socketio.on('user_prompt')
def handle_prompt(data):
    stream = jarvis.run_stream(data['prompt'])
    for chunk in stream:
        print(chunk, end="|", flush=True)
        emit("chunk", chunk)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3000, allow_unsafe_werkzeug=True)