from flask import Flask, request, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT_STT
import asyncio
import speech_to_text
import requests
import os
from audioProcessor import convert_webm_to_wav
import subprocess



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
    print(f"Received audio file: {audio_file.filename}")
    file_path = os.path.join("uploads", f"{audio_file.filename}")
    wav_file_path = file_path.rsplit('.', 1)[0] + '.wav'

    # Save the audio file if it's in the expected format
    if audio_file.filename.endswith('.webm'):
        # Save the original .webm file
        audio_file.save(file_path)
        try:
            # Convert the .webm file to .wav
            if os.path.exists(wav_file_path):
                os.remove(wav_file_path)
            convert_webm_to_wav(file_path, wav_file_path)
            file_path = wav_file_path  # Now the path will point to the converted .wav file
        except Exception as e:
            print(f"Error converting webm to wav: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # For other file types, save directly
        audio_file.save(file_path)

    # Process the converted .wav file (speech-to-text, etc.)
    try:
        text_result = speech_to_text.speech_to_text(filepath=wav_file_path)
    except Exception as e:
        print(f"Error during speech-to-text processing: {e}")
        return jsonify({"status": "error", "message": "Failed to process audio"}), 500

    # Send a POST request to notify main service about recording completion
    conversation_id = request.form.get("conversation_id")
    try:
        response = requests.post(f'http://llm-service:3000/recording_completed', json={
            "text": text_result,
            "conversation_id": conversation_id
        })
        response.raise_for_status()  # Ensure the request was successful
    except requests.exceptions.RequestException as e:
        print(f"Error notifying LLM service: {e}")
        return jsonify({"status": "error", "message": "Failed to notify LLM service"}), 500

    # Return the result to the client
    return jsonify({"status": "success", "message": text_result}), 200



# Routes end
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    socketio.run(app, debug=True, host='0.0.0.0', port=3001, allow_unsafe_werkzeug=True)