from openai import OpenAI
import os
from dotenv import load_dotenv
import numpy as np
import wave
from audioRecorder import AudioRecorder
import time

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def create_tmp_wav_file(chunk, rate=16000, channels=1):
    with wave.open("tmp.wav", 'wb') as wav_file:
        wav_file.setnchannels(channels)  # Mono audio
        wav_file.setsampwidth(2)  # 2 bytes per sample, assuming 16-bit audio
        wav_file.setframerate(rate)  # Assuming 16kHz sample rate
        wav_file.writeframes(chunk)

def remove_tmp_wav_file():
    if os.path.exists("tmp.wav"):
        os.remove("tmp.wav")

def speech_to_text(audio_file):
    transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file
    )

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



if __name__ == "__main__":
    CHUNK_SIZE = 1024  # Number of frames in a buffer
    RATE = 16000       # 16 000 Hz is a common rate for speech processing
    CHANNELS = 1       # Mono audio
    SILENCE_THRESHOLD = 8  # Used to detect silence for stopping recording
    MAX_SILENCE_DURATION = 5  # Seconds of silence to stop recording

    recorder = AudioRecorder(chunk_size=CHUNK_SIZE, rate=RATE, channels=CHANNELS, silence_threshold=SILENCE_THRESHOLD, max_silence_duration=MAX_SILENCE_DURATION)

    text = []
    for chunk in recorder.record():
        create_tmp_wav_file(chunk)
        audio_file = path_to_audio_file("tmp.wav")
        text.append(speech_to_text(audio_file=audio_file))
        audio_file.close()
        print(text[-1].text)

    time.sleep(2)

    remove_tmp_wav_file()

        
    # audio_file = path_to_audio_file("nb-whisper-main/nb-whisper-main/audio/erna.mp3")
    # transcription = speech_to_text(audio_file)
    # print(transcription.text)
    # audio_file.close()




