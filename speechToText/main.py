from flask import Flask, request, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from config import PORT_STT
import asyncio
import speech_to_text
import requests


app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret_key_xdddd'  # TODO: Make a better key
CORS(app, resources={r"/*": {"origins": "*"}})  # TODO: Make the CORS actually not accept everything
socketio = SocketIO(app, cors_allowed_origins="*") 

# Runs in multiple threads, printing the output, also appending the read text to the text list.
def handle_chunk(chunk, index):
    create_tmp_wav_file(chunk, path=f"tmp{index}.wav")
    processor = AudioProcessor(f"tmp{index}.wav")
    processor.process()
    processor.save_audio(f"tmp{index}.wav")
    audio_file = path_to_audio_file(f"tmp{index}.wav")

    text.append(speech_to_text(audio_file=audio_file))
    audio_file.close()
    print(text[-1].text)
    remove_tmp_wav_file(index)

# Routes

@app.route("/")
def hello_world():
    return app.send_static_file('index.html')


@app.route('/start_recording/<conversation_id>', methods=['POST'])
def start_recording_recorder(conversation_id):
    print(f"Recording started for conversation ID: {conversation_id}")

    try:
        # Start the recording process
        text = asyncio.run(speech_to_text.startRecording())  # Ensure this function is correctly defined

        # After recording, send a POST request back to the main service
        response = requests.post(f'http://llm-service:3000/recording_completed', json={"text": text, "conversation_id": conversation_id})
        
        if response.status_code != 200:
            print("Failed to notify main service about recording completion")
        
        return jsonify({"status": "success", "text": text}), 200

    except Exception as e:
        print(f'Something very bad happened: {e}')
        return jsonify({"status": "error", "text": "Recording failed"}), 500

# Routes end
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=PORT_STT, allow_unsafe_werkzeug=True)