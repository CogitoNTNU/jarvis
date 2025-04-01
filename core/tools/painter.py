import os
import config
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
import requests
from openai import OpenAI
from requests.exceptions import ConnectionError
import time
from base64 import b64decode

url = "http://stable-diffusion:7860/sdapi/v1/txt2img"

# Get absolute path to the static/ai_images directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory where script is located
output_folder = os.path.join(BASE_DIR, "..", "static", "ai_images")

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

def is_server_running():
    try:
        response = requests.get("http://stable-diffusion:7860/docs")
        return response.status_code == 200
    except:
        return False

@tool
def painter(prompt: str, neg_prompt: str, max_retries: int = 3):
    """
    Generates an image if the AI decides it would be helpful based on the given description.

    The AI will decide autonomously when to generate an image.
    If no image is needed, this tool won't be called.

    Parameters:
    - prompt (str): A detailed image description.
    - neg_prompt (str): A description of what to avoid in the image.

    Returns:
    - str: Path of the saved image or an error message.
    
    When image is generated. Answer the user with an html tag <img src="image_path"></img>
    """
    if not is_server_running():
        return "Error: Stable Diffusion API server is not running. Please start the server at localhost:7860"

    payload = {
        "prompt": prompt,
        "negative_prompt": neg_prompt,
        "steps": 20,
        "cfg_scale": 7.0,
        "width": 512,
        "height": 512,
        "sampler_index": "DPM++ 2M Karras"
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                image_data = b64decode(result["images"][0])

                # Save the image
                timestamp = int(time.time())
                image_path = os.path.join(output_folder, f"generated_image_{timestamp}.png")
                with open(image_path, "wb") as img_file:
                    img_file.write(image_data)

                return f"Image successfully saved at: {image_path}"
            else:
                return f"Image generation failed with status code {response.status_code}"
        except ConnectionError:
            if attempt == max_retries - 1:
                return "Error: Could not connect to Stable Diffusion API. Please ensure the server is running at localhost:7860"
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            return f"Error: Unexpected error occurred - {str(e)}"
