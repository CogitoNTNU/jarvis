import os
import socket
import struct
import hashlib
from loguru import logger
from pydub import AudioSegment
from pydub.utils import make_chunks
import subprocess
import queue
import threading
from flask import jsonify, request, Flask
import time
from narakeet import narakeet

# Network parameters
RECEIVER_IP = os.environ.get('RECEIVER_IP')
RECEIVER_PORT = os.environ.get('RECEIVER_PORT')
TTS_ENGINE = os.environ.get('TTS_ENGINE')
NARAKEET_API_KEY = os.environ.get('NARAKEET_API_KEY')
CACHING_MAX_SIZE = os.environ.get('CACHING_MAX_SIZE')
# Validate environment variables
if not RECEIVER_IP:
    raise ValueError("RECEIVER_IP environment variable is not set")

if not RECEIVER_PORT:
    raise ValueError("RECEIVER_PORT environment variable is not set")
try:
    RECEIVER_PORT = int(RECEIVER_PORT)
except ValueError:
    raise ValueError("RECEIVER_PORT must be a valid integer")

if not TTS_ENGINE:
    raise ValueError("TTS_ENGINE environment variable is not set")
if TTS_ENGINE not in ['narakeet', 'espeak']:
    raise ValueError("TTS_ENGINE must be either 'narakeet' or 'espeak'")

if TTS_ENGINE == 'narakeet' and not NARAKEET_API_KEY:
    raise ValueError("NARAKEET_API_KEY environment variable is not set, but TTS_ENGINE is set to 'narakeet'")

caching_directory = "/cache"

if CACHING_MAX_SIZE:
    try:
        CACHING_MAX_SIZE = int(CACHING_MAX_SIZE)
        if CACHING_MAX_SIZE <= 0:
            raise ValueError("CACHING_MAX_SIZE must be a positive integer")
    except ValueError:
        raise ValueError("CACHING_MAX_SIZE must be a valid positive integer")
    
    logger.info(f"Caching enabled. Max cache size: {CACHING_MAX_SIZE} MB")
else:
    logger.info("Caching disabled")


    
def generate_audio(text: str) -> AudioSegment:
    if CACHING_MAX_SIZE:
        sha256_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_file = os.path.join(caching_directory, f"{sha256_hash}.mp3")
        
        if os.path.exists(cache_file):
            logger.info(f"Cache hit for text: {text[:30]}...")
            audio = AudioSegment.from_mp3(cache_file)
            # Update the access time of the file
            os.utime(cache_file, None)
            return audio
        
        logger.info(f"Cache miss for text: {text[:30]}...")
    
    # Generate new audio
    if TTS_ENGINE == 'espeak':
        subprocess.run(['espeak-ng', '-v', 'en', '-s', '150', '-w', 'temp.mp3', text], check=True)
        audio = AudioSegment.from_mp3('temp.mp3')
    elif TTS_ENGINE == 'narakeet':
        narakeet(text, 'temp.mp3', api_key=NARAKEET_API_KEY)
        audio = AudioSegment.from_mp3('temp.mp3')
    elif TTS_ENGINE == 'openai':
        raise NotImplementedError("OpenAI TTS is not implemented yet")
        # TODO: Implement OpenAI TTS
        audio = AudioSegment.from_mp3('temp.mp3')

    
    if CACHING_MAX_SIZE:
        # Add the new file to the cache
        audio.export(cache_file, format="mp3")
        logger.info(f"Added new file to cache: {cache_file}")
        
        # Check cache size and remove oldest files if necessary
        cache_files = [os.path.join(caching_directory, f) for f in os.listdir(caching_directory) if f.endswith('.mp3')]
        cache_files.sort(key=lambda x: os.path.getatime(x))
        
        total_size = sum(os.path.getsize(f) for f in cache_files)
        while total_size > CACHING_MAX_SIZE * 1024 * 1024:  # Convert MB to bytes
            oldest_file = cache_files.pop(0)
            file_size = os.path.getsize(oldest_file)
            os.remove(oldest_file)
            total_size -= file_size
            logger.info(f"Removed oldest file from cache: {oldest_file} (size: {file_size / 1024 / 1024:.2f} MB)")
        
        logger.info(f"Current cache size: {total_size / 1024 / 1024:.2f} MB")
    
    return audio


def generate_tts_thread(input_queue, output_queue):
    while True: 
        text = input_queue.get()
        print("Generating TTS")

        audio = generate_audio(text)

        
        print("TTS generated")

        audio = audio.set_channels(2).set_frame_rate(44100).set_sample_width(2)

        output_queue.put(audio)
        print("TTS put in queue")


def audio_sender_thread(audio_queue:queue.Queue):
    while True:
        if not audio_queue.empty():
            audio = audio_queue.get()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((RECEIVER_IP, RECEIVER_PORT))
        
            print("Sending audio")
            for chunk in make_chunks(audio, 1024):
                print("Sending chunk")
                raw_data = chunk.raw_data
                sock.sendall(struct.pack('!I', len(raw_data)))
                sock.sendall(raw_data)
        
            sock.close()
        else:
            time.sleep(0.1)

audio_queue = queue.Queue()
tts_queue = queue.Queue()

threading.Thread(target=generate_tts_thread, args=(tts_queue, audio_queue)).start()
threading.Thread(target=audio_sender_thread, args=(audio_queue,)).start()


app = Flask(__name__)

@app.route('/tts', methods=['POST'])
def text_to_speech():
    data = request.json
    if 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    print("Got input: " + data['text'])
    for sentence in data['text'].split('.'): 
        tts_queue.put(sentence)
    return jsonify({"message": "Text received and processing started"}), 202

if __name__ == '__main__':
    logger.info("Starting TTS server")
    logger.info(f"RECEIVER_IP: {RECEIVER_IP}")
    logger.info(f"RECEIVER_PORT: {RECEIVER_PORT}")
    logger.info(f"TTS_ENGINE: {TTS_ENGINE}")
    if CACHING_MAX_SIZE:
        logger.info(f"CACHING_MAX_SIZE: {CACHING_MAX_SIZE}")
    app.run(debug=True, port=5000, host='0.0.0.0')
