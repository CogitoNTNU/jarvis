'''
    Relies on youtube-transcript-api using the unofficial youtube web-client internal api.
    This may change without warning.
    https://github.com/jdepoix/youtube-transcript-api
    Used for now because of simplicity of getting transcripts without an api-key, but instead using the browser cookie.
    TODO: Port to youtube's official api using an api-key. Less flexible, but more stable.
    Official youtube data api for captions: https://developers.google.com/youtube/v3/docs/captions
'''

from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

from youtube_transcript_api import YouTubeTranscriptApi
import json

video_id = ""

@tool
def youtube_transcript(video_id: str) -> str:
    """
    Get a youtube video transcript as english text.

    Args: 
        video_id: The video ID from the url. Usually looks like: 'galcZShN268' or '3nNpR_kj51o'
    """
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id) # By default grabs the english transcript. Can grab a different langauge.
    transcript: str = "" 
    for sentence in transcript_list:
        transcript += " " + sentence['text']

    "TODO: Pass it through an LLM to fix punctuation, making it more digestible for analysis. Maybe break it into chapters"

    return transcript

def get_youtube_transcript() -> StructuredTool:
    return youtube_transcript