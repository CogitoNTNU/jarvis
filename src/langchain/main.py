from flask import Flask, request, url_for
from src.langchain.agent import Agent
from src.langchain.models import Model

jarvis = Agent(Model.gpt_35)

def prompt_jarvis(prompt) -> str:
    """
    A function that prompts the llm agent with the argument given and returns the response
    """
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
    app.run(debug=True, host='0.0.0.0')
    #app.run(debug=True, port='placeholder', host='placeholder')