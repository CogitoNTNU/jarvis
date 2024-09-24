from flask import Flask, request, url_for
from agent import Agent
from models import Model
from flask_socketio import SocketIO
from flask_cors import CORS




jarvis = Agent(Model.gpt_4o) # API key is configured in agent.py

def prompt_jarvis(prompt) -> str:
    """
    A function that prompts the llm agent with the argument given and returns the response
    """
    return jarvis.run(prompt)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for WebSocket

@app.route("/")
def hello_world():
    return 'Hello from Jarvis'

@app.route('/send_message', methods=['POST', 'GET'])
def llm_request():
    if(request.method == 'POST'):
        data = request.json
        print(data)
        print(data['message'])
        ai_message = prompt_jarvis(data['message'])
        
        return {"message": ai_message}

@socketio.event
def connect():
    print('Client connected')

@socketio.event
def disconnect():
    print('Client disconnected')

@socketio.on('message', namespace='/')
def handle_message(data):
    print('Received message:', data)
    socketio.emit('response', 'Server received your message: ' + str(data))

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3001, allow_unsafe_werkzeug=True)
    #app.run(debug=True, port='placeholder', host='placeholder')