import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
import seaborn as sns
import librosa
import librosa.display

def analyze_audio(audio_path):
    # Load the WAV file
    sr, audio_data = wavfile.read(audio_path)

    # If stereo, take only one channel (convert to mono)
    if len(audio_data.shape) == 2:
        audio_data = audio_data.mean(axis=1)
    
    # Normalize audio data to range between -1 and 1
    audio_data = audio_data / np.max(np.abs(audio_data))


    
    # Plot the spectrogram
    audio_data_librosa, _ = librosa.load(audio_path, sr=sr)
    D = librosa.amplitude_to_db(np.abs(librosa.stft(audio_data_librosa)), ref=np.max)
    librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log')
    plt.colorbar(format='%+2.0f dB')
    plt.title('Spectrogram')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python audio_analysis.py <audio_file>")
        sys.exit(1)

    audio_path = sys.argv[1]
    analyze_audio(audio_path)
    if len(sys.argv) > 2:
        audio_path2 = sys.argv[2]
        analyze_audio(audio_path2)
