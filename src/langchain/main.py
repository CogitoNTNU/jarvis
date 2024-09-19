from flask import Flask, request
from src.langchain.agent import Agent
from src.langchain.models import Model

jarvis = Agent(Model.gpt_35)

def prompt_jarvis(prompt) -> str:
    return jarvis.run(prompt)


app = Flask(__name__)

@app.route("/")
def hello_world():
    return 'Hello from Jarvis'

@app.route('/send_message', methods=['POST', 'GET'])
def llm_request():
    if(request.method == 'POST'):
        data = request.json
        print(data)
        print(data['message'])
        ai_message = prompt_jarvis(data['message'])
        return {"message": ai_message}

if __name__ == '__main__':
    app.run(debug=True, port='placeholder', host='placeholder')

