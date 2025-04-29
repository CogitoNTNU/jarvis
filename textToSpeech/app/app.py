from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from logging_config import logger
from threading import Thread, Lock
from queue import Queue
import tts
import os
from typing import List, Tuple
import logging
from flask_cors import CORS

# Global counter for sentence IDs
sentence_counter: int = 0
counter_lock = Lock()

# Add these global variables after the existing ones
recent_audio_chunks: dict[int, list] = {}  # Store recent chunks
MAX_STORED_CHUNKS: int = 100  # Limit how many chunks we store


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using basic string splitting"""
    # Split on common sentence endings
    raw_sentences: List[str] = []
    for part in text.replace('!', '.').replace('?', '.').split('.'):
        cleaned = part.strip()
        if cleaned:  # Only add non-empty sentences
            raw_sentences.append(cleaned)
    return raw_sentences


def generator_thread(input_queue: Queue, output_queue: Queue, tts_engine: tts.TTS) -> None:
    # TODO port this to asyncio
    while True:
        item = input_queue.get()
        if item is None:
            break
        sentence_id, sentence = item
        audio_data = tts_engine.tts(sentence)
        output_queue.put((sentence_id, audio_data))


def streamer_thread(input_queue: Queue) -> None:
    expected_id: int = 1
    buffer: dict[int, list] = {}

    while True:
        item = input_queue.get()
        if item is None:
            break

        sentence_id, audio_data = item
        # print(f"Got audio chunk {sentence_id}")

        # Reset expected_id if we're starting a new text generation
        if sentence_id == 1:
            expected_id = 1
            buffer.clear()  # Clear any old buffered chunks
            print("New text generation - resetting counters")

        # If this is the chunk we're waiting for, emit it
        if sentence_id == expected_id:
            try:
                audio_list = list(audio_data)
                # print(f"Emitting chunk {sentence_id} to clients")
                socketio.emit('audio_stream', {
                    'audio_data': audio_list,
                    'sentence_id': sentence_id
                }, namespace='/')
                # print(f"Emitted chunk {sentence_id}")
                expected_id += 1

                # Process buffered chunks
                while expected_id in buffer:
                    buffered_audio = buffer.pop(expected_id)
                    socketio.emit('audio_stream', {
                        'audio_data': buffered_audio,
                        'sentence_id': expected_id
                    }, namespace='/')
                    expected_id += 1

            except Exception as e:
                print(f"Error emitting audio: {str(e)}")
                import traceback
                traceback.print_exc()

        # If this chunk is for a future sentence, buffer it
        elif sentence_id > expected_id:
            buffer[sentence_id] = list(audio_data)
        else:
            print(f"Dropping late chunk for sentence {sentence_id}")


app: Flask = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'lklsa01lkJASD9012o3khj123l'
socketio: SocketIO = SocketIO(
    app,
    cors_allowed_origins="*",
    logger=False,  # Set to True to log hella verbose
    engineio_logger=False,  # Same with this one
    ping_timeout=10,
    ping_interval=5,
    async_mode='threading',
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1000
)
input_queue: Queue = Queue()
output_queue: Queue = Queue()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    global sentence_counter
    try:
        data = request.get_json()
        text: str = data.get('text', '')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        sentences: List[str] = split_into_sentences(text)
        queue_items: List[Tuple[int, str]] = []

        with counter_lock:
            # Reset sentence counter if it's a new session
            sentence_counter = 0  # Reset counter
            for sentence in sentences:
                sentence_counter += 1
                queue_item = (sentence_counter, sentence)
                queue_items.append(queue_item)
                input_queue.put(queue_item)
                print(f"Queuing sentence {sentence_counter}: {
                      sentence[:30]}...")  # Debug print

        return jsonify({
            'message': 'Text queued successfully',
            'sentences': len(sentences),
            'queue_items': queue_items
        }), 200

    except Exception as e:
        print(f"Error in generate endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500


@socketio.on('audio_data')
def handle_audio_data(data: bytes) -> None:
    # Broadcast the received audio data to all connected clients
    emit('audio_stream', data, broadcast=True)


# Add this new route to test Socket.IO
@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    print(f"New client connected: {client_id}")  # More detailed connection log
    socketio.emit('test', {'data': 'Test message'})


# Add a health check route
# For docker healthchecks
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':

    import logging
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('engineio').setLevel(logging.INFO)
    logging.getLogger('socketio').setLevel(logging.INFO)

    logger.info("Starting server...")

    if os.getenv("TTS_ENABLED") != "true":
        logger.info("ENV variable TTS_ENABLED not set or set to 'false'")
        exit();

    if os.getenv("REDIS_URL"):
        cache = tts.Cache(os.getenv("REDIS_URL"), max_size_mb=1000)
    else:
        cache = None

    if os.getenv("NARAKEET_API_KEY"):
        tts = tts.Narakeet(
            api_key=os.getenv("NARAKEET_API_KEY"), cache=cache)
    elif os.getenv("OPENAI_API_KEY"):
        tts = tts.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"), cache=cache)
    else:
        tts = tts.Espeak()


    if os.getenv("DEBUG") == "True":
        debug = True
    else:
        debug = False

    generator_thread = Thread(target=generator_thread,
                              args=(input_queue, output_queue, tts))
    generator_thread.daemon = True  # Make thread daemon
    generator_thread.start()

    streamer_thread = Thread(target=streamer_thread, args=(output_queue,))
    streamer_thread.daemon = True  # Make thread daemon
    streamer_thread.start()

    print("All threads started, running server...")
    socketio.run(app, debug=debug, host='0.0.0.0',
                 port=5000, allow_unsafe_werkzeug=True)
