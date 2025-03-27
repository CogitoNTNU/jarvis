
#Tool that uses either online image generation API or local image generation (default)
#Show the image using a port (temporary solution)
#Let the program arbitrarily decide whether to use generate image or not (perhaps in another tool?)

import config
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

import requests

url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

payload = {
    "prompt": "a futuristic city skyline at sunset",
    "negative_prompt": "blurry, low quality",
    "steps": 20,
    "cfg_scale": 7.0,
    "width": 512,
    "height": 512,
    "sampler_index": "DPM++ 2M Karras"
}

response = requests.post(url, json=payload)
result = response.json()



