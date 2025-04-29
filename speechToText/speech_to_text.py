from openai import OpenAI
import os
from dotenv import load_dotenv
from audioRecorder import AudioRecorder
from audioProcessor import AudioProcessor


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def speech_to_text(audio_file = None, filepath = None):
    if audio_file is None:
        if filepath is None:
            raise ValueError("Either audio_file or filepath must be provided")
        audio_file = path_to_audio_file(filepath)
    #audio_file=handle_audio(audio_file, path=filepath)

    prompt="Transcribe the following Norwegian speech to text, the sentances may be cut off, do not make up words or fill in the sentances"
    transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file, 
    language="en", 
    )
    transcription.text.replace(prompt, "")
    return transcription.text

def path_to_audio_file(path):
    audio_file = open(path, "rb")
    return audio_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) ==1:
        print("NOPE")
    else:
        audio_file = path_to_audio_file(sys.argv[1])
        transcription = speech_to_text(audio_file)
        print(transcription.text)
        audio_file.close()

        
    # audio_file = path_to_audio_file("nb-whisper-main/nb-whisper-main/audio/erna.mp3")
    # transcription = speech_to_text(audio_file)
    # print(transcription.text)
    # audio_file.close()