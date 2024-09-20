import numpy as np
import wave
from scipy.io import wavfile
import noisereduce as nr

class AudioProcessor:
    def __init__(self, audio_file=None, audio_path=None):
        if audio_file:
            if isinstance(audio_file, np.ndarray):
                self.audio = audio_file
            else:
                raise ValueError("Audio file must be a numpy array when passed directly.")
        elif audio_path:
            self.load_audio(audio_path)
        else:
            self.audio = None

    def load_audio(self, audio_path):
        self.sr, self.audio = wavfile.read(audio_path) 
    
    def verify_audio(self):
        if self.audio is None or not isinstance(self.audio, np.ndarray):
            raise ValueError("No valid audio loaded.")

    def reduce_noise(self):
        self.verify_audio()
        reduced_noise = nr.reduce_noise(y=self.audio, sr=self.sr)
        self.audio = reduced_noise.astype(np.int16) 

    def save_audio(self, output_path):
        self.verify_audio()
        wavfile.write(output_path, self.sr, self.audio)

    def process(self):
        self.reduce_noise()

# for debugging
if __name__ == "__main__":

    def boost_audio(audio, factor=1.5):
        boosted_audio = audio * factor
        return np.clip(boosted_audio, -32768, 32767).astype(np.int16)

    import sys
    boosting = False
    if len(sys.argv) >= 4 and sys.argv[1] == "boost":
        boosting = True
        sample_rate, audio = wavfile.read(sys.argv[2])
        
        boosted_audio = boost_audio(audio, float(sys.argv[3]))
        
        wavfile.write("b_" + sys.argv[2], sample_rate, boosted_audio)
    if not boosting:

        if len(sys.argv) < 3:
            print("Usage: python AudioProcessor.py <input_path> <output_path>")
            sys.exit(1)

        input_path = sys.argv[1]
        output_path = sys.argv[2]
        
        # Initialize processor
        processor = AudioProcessor(audio_path=input_path)
        processor.process()
        processor.save_audio(output_path)

