from flask import Flask, request, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT_STT
import asyncio
import speech_to_text
import requests
import os


app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*") 


# Routes
@app.route("/")
def hello_world():
    return app.send_static_file('index.html')


@app.route('/start_recording/<conversation_id>', methods=['POST'])
def start_recording(conversation_id):
    print(f"Recording triggered for conversation ID: {conversation_id}")
    
    try:
        # Emit 'start_recording' event to clients
        socketio.emit('start_recording', {'conversation_id': conversation_id})
        
        return jsonify({"status": "success", "message": "Recording started on client"}), 200

    except Exception as e:
        print(f'Error starting recording: {e}')
        return jsonify({"status": "error", "message": "Failed to start recording"}), 500


@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    audio_file = request.files['audio']
    conversation_id = request.form.get("conversation_id")
    file_path = os.path.join("uploads", f"recording.wav")
    audio_file.save(file_path)
    
    # Placeholder for processing the audio if needed
    text_result = speech_to_text.speech_to_text(file_path)
    
    # Send a POST request to notify main service about recording completion
    requests.post(f'http://llm-service:3000/recording_completed', json={
        "text": text_result,
        "conversation_id": conversation_id
    })
    
    return jsonify({"status": "success", "message": text_result}), 200


# Routes end
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    socketio.run(app, debug=True, host='0.0.0.0', port=PORT_STT, allow_unsafe_werkzeug=True)