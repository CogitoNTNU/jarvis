from flask import Flask, request, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from flask_cors import CORS
from audioRecorder import AudioRecorder
from threading import Thread
import time
from speech_to_text import create_tmp_wav_file, remove_tmp_wav_file, speech_to_text, path_to_audio_file
from audioProcessor import AudioProcessor

# Global for now. TODO: Make this not global ;)
text = []

# Debug purposes
try:
    PORT
except:
    PORT = 3001

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
def start_listening_for_audio():
    print("Listening for audio:")
    try:
        recorder = AudioRecorder(chunk_size=1024, rate=16000, channels=1, silence_threshold=25, max_silence_duration=2)
    except Exception as e:
        print(e)
    # Adjust silence duration and threshold for tweaking responsiveness
    index = 0
    for chunk in recorder.record(10):
        t = Thread(target=handle_chunk, args=(chunk,index))
        print(t)
        index += 1
        t.start()
    time.sleep(2)

# Routes end
if __name__ == '__main__':
    #socketio.run(app, debug=True, host='0.0.0.0', port=PORT, allow_unsafe_werkzeug=True)
    start_listening_for_audio()