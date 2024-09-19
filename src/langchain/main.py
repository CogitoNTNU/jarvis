from flask import Flask
import agent
import models

jarvis = agent.Agent(models.Model.gpt_35)

def prompt_jarvis(prompt: str) -> str:
    return jarvis.run(prompt)


app = Flask(__name__)

@app.route("/")
def hello_world():
    return 'Hello from Jarvis'


