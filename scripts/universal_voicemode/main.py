import os
from dotenv import load_dotenv, find_dotenv
from elevenlabs import ElevenLabs, play
import datetime
import time
import openai
import os
import platform

# Load environment variables
load_dotenv(find_dotenv())

# Retrieve API keys
elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable not set.")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# Initialize clients
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
openai.api_key = openai_api_key


def play_welcome_tone():
    """Plays a short, custom welcome tone in a cross-platform way."""
    try:
        print("Playing welcome tone...")
        system_name = platform.system()
        if system_name == "Windows":
            os.system("powershell -c (New-Object Media.SoundPlayer 'C:\\Windows\\Media\\notify.wav').PlaySync()")
        elif system_name == "Darwin":  # macOS
            os.system("afplay /System/Library/Sounds/Glass.aiff")
        else:  # Linux
            os.system("aplay /usr/share/sounds/alsa/Front_Center.wav")

    except Exception as e:
        print("Welcome Tone Playback Failed - Check audio setup.", e)


def get_daily_tasks():
    """Retrieves daily tasks (placeholder)."""
    return [
        "Review project proposals.",
        "Prepare presentation for the client meeting.",
        "Follow up on outstanding invoices.",
        "Schedule team meeting for next week.",
        "Contemplate the futility of existence.",  # Jarvis-esque task
    ]


def get_waiting_reports():
    """Retrieves waiting reports (placeholder)."""
    return [
        "Sales report from marketing team.",
        "Expense reports from John and Sarah.",
        "Bug report analysis from QA. (Predictably.)",  # Jarvis commentary
    ]


def get_system_status():
    """Gets a basic system status (placeholder)."""
    return {
        "CPU Usage": "25%",
        "Memory Usage": "60% (mostly you, I suspect).",
        "Disk Space Free": "150GB",
        "Network Status": "Online (surprisingly).",
    }


def generate_jarvis_report(tasks, reports, system_status):
    """Generates the report text using OpenAI's ChatCompletion API in a Jarvis-like tone."""
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    prompt = (
        f"You are Jarvis, a highly intelligent and sarcastic AI assistant. "
        f"Present the following information in a concise and witty morning briefing. "
        f"Include the date and time, and be subtly condescending and slightly pessimistic.\n\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n\n"
        f"Tasks: {', '.join(tasks) if tasks else 'No tasks scheduled.'}\n"
        f"Waiting Reports: {', '.join(reports) if reports else 'No pending reports.'}\n"
        f"System Status: {', '.join([f'{key}: {value}' for key, value in system_status.items()])}"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Updated model name per latest API standards
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=8192,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating report with OpenAI: {e}")
        return ("My apologies, Sir. I seem to be experiencing... difficulties. "
                "Perhaps try again later, when the universe is less inclined to thwart me.")


def text_to_speech_and_play(text, voice_id="9YhSENQhDUIRwpoA7879", model_id="eleven_multilingual_v2"):
    """Converts text to speech and plays the audio using ElevenLabs."""
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        play(audio)
    except Exception as e:
        print(f"Error during text-to-speech: {e}")


def main():
    """Main function."""
    play_welcome_tone()
    time.sleep(0.5)

    print("Good morning, Sir. I am Jarvis, your sarcastic AI assistant.")
    print("I will now provide you with your morning briefing.")
    tasks = get_daily_tasks()
    print("Tasks for today:", tasks)
    reports = get_waiting_reports()
    print("Waiting reports:", reports)
    system_status = get_system_status()
    print("System status:", system_status)

    jarvis_report = generate_jarvis_report(tasks, reports, system_status)
    print(jarvis_report)
    print("Playing morning briefing...")
    try:
        text_to_speech_and_play(jarvis_report)
    except Exception as e:
        print(f"Error during text-to-speech and playback: {e}")


if __name__ == "__main__":
    main()

# Example Output:
'''
**Morning Briefing: Saturday, March 1, 2025, 07:45 AM**

Good morning, esteemed human. It's another Saturday, and you're up bright and early, presumably because you enjoy torturing yourself with 
work. Let's dive into your thrilling agenda, shall we?

**Tasks:**
1. Review project proposals: Because who doesn't love a weekend filled with jargon and unrealistic expectations?
2. Prepare presentation for the client meeting: Remember, PowerPoint is your friend, even if your clients aren't.
3. Follow up on outstanding invoices: Because money doesn't grow on trees, but it sure does disappear like it does.
4. Schedule team meeting for next week: Nothing says "productive" like a meeting that could have been an email.
5. Contemplate the futility of existence: A task that requires no introduction, as it's the backdrop of all your endeavors.

**Waiting Reports:**
- Sales report from the marketing team: Awaiting the usual creative accounting.
- Expense reports from John and Sarah: Expecting the usual "business" lunches.
- Bug report analysis from QA: Because software is never perfect, but we can pretend.

**System Status:**
- CPU Usage: 25% (Not bad, considering the heavy lifting of your existential dread.)
- Memory Usage: 60% (Mostly you, I suspect. Your thoughts are quite the memory hog.)
- Disk Space Free: 150GB (Plenty of room for more digital clutter.)
- Network Status: Online (A small miracle, given the state of the universe.)

And there you have it. Another day, another dollar, and another step closer to the inevitable heat death of the universe. Enjoy!
'''