import pyaudio
import time
import numpy as np
import sys


class AudioRecorder:
    def __init__(self, chunk_size=1024, rate=16000, channels=1, silence_threshold=500, max_silence_duration=5):
        self.chunk_size = chunk_size
        self.rate = rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.max_silence_duration = max_silence_duration

        self.audio_chunks = []

    def start_recording(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.chunk_size)
        self.audio_chunks = []
        print("Recording started")


    def stop_recording(self):
        self.stream.stop_stream()
        self.stream.close()
        print("Recording stopped")

    def silent(self, data):
        audio_data = np.frombuffer(data, dtype=np.int16)
        if np.isnan(audio_data).any():
            return True
        rms = np.sqrt(np.mean(audio_data ** 2))
        # sys.stdout.write(f"\rRMS: {rms}")
        # sys.stdout.flush()
        return rms < self.silence_threshold
    
    def record(self, MERGE_SIZE=60, min_frames_with_sound=10):
        self.start_recording()

        self.audio_chunks = []
        silence_start = None
        frames_with_sound = 0
        
        try:
            while True:
                data = self.stream.read(self.chunk_size)
                self.audio_chunks.append(data)
            
                if self.silent(data):

                    if silence_start is None:
                        silence_start = time.time()
                    
                    if len(self.audio_chunks) >= MERGE_SIZE and time.time() - silence_start > 0.2:
                        if frames_with_sound > min_frames_with_sound:
                            yield b''.join(self.audio_chunks)  
                            frames_with_sound = 0
                        self.audio_chunks = []
                        

                    elif time.time() - silence_start > self.max_silence_duration:   
                        print(f"Silence detected for more than {self.max_silence_duration} seconds, stopping recording.")
                        break
                else:
                    silence_start = None
                    frames_with_sound += 1

        except KeyboardInterrupt:
            print("Recording stopped by user.")
        finally:
            self.stop_recording()

        return self.audio_chunks
