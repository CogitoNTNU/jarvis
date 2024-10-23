import requests
import time
import os
from loguru import logger


def narakeet(text,filename,api_key,voice='harry',speed=1):
    url = f'https://api.narakeet.com/text-to-speech/mp3?voice={voice}&voice-speed={speed}'
    options = {
        'headers': {
            'Accept': 'application/octet-stream',
            'Content-Type': 'text/plain',
            'x-api-key': api_key,
        },
        'data': text.encode('utf8')
    }

    start_time = time.time()
    response = requests.post(url, **options)
    if response.status_code != 200:
        raise ValueError(f"Failed to generate TTS: {response.status_code} {response.text}")
    end_time = time.time()
    logger.info(f"TTS generated in {end_time - start_time} seconds")
    
    with open(filename, 'wb') as f:
        f.write(response.content)



