import numpy as np
import wave
from scipy.io import wavfile
import noisereduce as nr
from silero_vad import load_silero_vad, get_speech_timestamps, read_audio
from scipy.signal import resample





class AudioProcessor:
    def __init__(self, audio_path=None):
        if audio_path is not None:
            self.load_audio(audio_path)
        else:
            self.audio_path = None
            self.sr = None
            self.audio = None

    def load_audio(self, audio_path):
        self.audio_path = audio_path
        self.audio = read_audio(audio_path)

    # so far, very shit
    def reduce_noise(self):
        reduced_noise = nr.reduce_noise(y=self.audio, sr=16000)
        scaled_audio = np.int16(reduced_noise * 32767)
        self.audio = scaled_audio


    def save_audio(self, output_path):
        wavfile.write(output_path, 16000, self.audio)

    def remove_silence(self, output_path=None):
        model = load_silero_vad()
        wav = read_audio(self.audio_path)
        speech_timestamps = get_speech_timestamps(wav, model)
        speech_segments = [wav[segment['start']:segment['end']] for segment in speech_timestamps]
        combined_speech = np.concatenate(speech_segments)

        if output_path is not None:
            wavfile.write(output_path, 16000, combined_speech)
        else:
            self.audio = combined_speech

           
    def boost_audio(self, factor=1.5):
        boosted_audio = self.audio * factor
        self.audio= np.clip(boosted_audio, -32768, 32767).astype(np.int16)
        
    def verify_audio_long_enough(self, length=16000):
        if len(self.audio) < length:
            return False
        return True

    def process(self):
        self.remove_silence()
        #self.reduce_noise()
        #self.boost_audio()
        
        return self.verify_audio_long_enough()

# for debugging
if __name__ == "__main__":

    import sys
    boosting = False
    remove_silence = False
    if len(sys.argv) >= 4 and sys.argv[1] == "boost":
        boosting = True
        processor = AudioProcessor(audio_path=sys.argv[2])
        
        
        boosted_audio = processor.boost_audio(float(sys.argv[3]))
        processor.save_audio("boosted.wav")
        
    elif len(sys.argv) >= 4 and sys.argv[1] == "silence":
        remove_silence = True
        processor = AudioProcessor(audio_path=sys.argv[2])
        processor.remove_silence(sys.argv[3])

    if not boosting and not remove_silence:

        if len(sys.argv) < 3:
            print("Usage: python AudioProcessor.py <input_path> <output_path>")
            sys.exit(1)

        input_path = sys.argv[1]
        output_path = sys.argv[2]
        
        # Initialize processor
        processor = AudioProcessor(audio_path=input_path)
        audio_enough = processor.process()
        if audio_enough == False:
            print("Audio too short")
        else:
            processor.save_audio(output_path)

