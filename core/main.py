from flask import Flask, request, url_for
from agent import Agent
from models import Model
from summarize_chat import summarize_chat
from rag import embed_and_store

jarvis = Agent(Model.gpt_4o) # API key is configured in agent.py

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

@app.route('/vectorize_chat', methods=['POST'])
def summarize_store():
    data = request.json
    chat_history = data.get('chat_history')
    user_id = data.get('user_id')

    if not chat_history or not user_id:
        return {"error": "chat_history and user_id are required"}, 400

    summary = summarize_chat(chat_history)
    embed_and_store(summary, user_id)

    return {"status": "success", "summary": summary}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='3001')
    #app.run(debug=True, port='placeholder', host='placeholder')