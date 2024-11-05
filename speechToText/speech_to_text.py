from openai import OpenAI
import os
from dotenv import load_dotenv
import numpy as np
import wave
from audioRecorder import AudioRecorder
from audioProcessor import AudioProcessor
import time
from threading import Thread

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_tmp_wav_file(chunk, rate=16000, channels=1, path="tmp.wav"):
    with wave.open(path, 'wb') as wav_file:
        wav_file.setnchannels(channels)  # Mono audio
        wav_file.setsampwidth(2)  # 2 bytes per sample, assuming 16-bit audio
        wav_file.setframerate(rate)  # Assuming 16kHz sample rate
        wav_file.writeframes(chunk)

def remove_tmp_wav_file(index=None):
    if index is not None:
        if os.path.exists(f"tmp{index}.wav"):
            os.remove(f"tmp{index}.wav")
    else:
        if os.path.exists("tmp.wav"):
            os.remove("tmp.wav")

def speech_to_text(audio_file = None, filepath = None):
    if audio_file is None and filepath is None:
        raise ValueError("Either audio_file or filepath must be provided")
    if audio_file is None:
        audio_file = path_to_audio_file(f"{filepath}")
    if filepath is None:
        filepath = "tmp.wav"
    handle_audio(audio_file, path=filepath)

    prompt="Transcribe the following Norwegian speech to text, the sentances may be cut off, do not make up words or fill in the sentances"
    transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file, 
    language="no", 
    prompt=prompt,
    )
    transcription.text.replace(prompt, "")
    return transcription

def path_to_audio_file(path):
    audio_file = open(path, "rb")
    return audio_file

def chunks_to_text(chunks):
    text = []
    for chunk in chunks:
        audio = np.frombuffer(chunk, np.int16)
        text.append(speech_to_text(audio))
    return text

def chunks_to_full_audio(chunks):
    return b"".join(chunks)


def handle_chunk(chunk, index, text):
    create_tmp_wav_file(chunk, path=f"tmp{index}.wav")
    processor = AudioProcessor(f"tmp{index}.wav")
    processor.process()
    processor.save_audio(f"tmp{index}.wav")
    audio_file = path_to_audio_file(f"tmp{index}.wav")

    text.append(speech_to_text(audio_file=audio_file))
    audio_file.close()
    print(text[-1].text)
    remove_tmp_wav_file(index)

def handle_audio(audio_file, path="tmp.wav"):
    processor = AudioProcessor(audio_file)
    processor.process()
    processor.save_audio(path)
    audio_file = path_to_audio_file(path)
    return audio_file


async def startRecording():
    CHUNK_SIZE = 1024  # Number of frames in a buffer
    RATE = 16000       # 16 000 Hz is a common rate for speech processing
    CHANNELS = 1       # Mono audio
    SILENCE_THRESHOLD = 25  # Used to detect silence for stopping recording
    MAX_SILENCE_DURATION = 5  # Seconds of silence to stop recording
    return "can you hear me?"
    recorder = AudioRecorder(chunk_size=CHUNK_SIZE, rate=RATE, channels=CHANNELS, silence_threshold=SILENCE_THRESHOLD, max_silence_duration=MAX_SILENCE_DURATION)
    
    text = []
    threads = []
    index = 0
    for chunk in recorder.record(30):
        t = Thread(target=handle_chunk, args=(chunk,index,text))
        threads.append(t)
        index += 1
        t.start()

    for t in threads:
        t.join()
    return " ".join([t.text for t in text])
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) ==1:
        startRecording()
    else:
        audio_file = path_to_audio_file(sys.argv[1])
        transcription = speech_to_text(audio_file)
        print(transcription.text)
        audio_file.close()

        
    # audio_file = path_to_audio_file("nb-whisper-main/nb-whisper-main/audio/erna.mp3")
    # transcription = speech_to_text(audio_file)
    # print(transcription.text)
    # audio_file.close()