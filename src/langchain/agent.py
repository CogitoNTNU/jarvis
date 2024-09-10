from langchain_openai import ChatOpenAI
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

import json
import os

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class JarvisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=OPENAI_API_KEY,  # if you prefer to pass api key in directly instaed of using env vars
            # base_url="...",
            # organization="...",
            # other params...
        )
        self.chat_history_path: str = "./chat_history.json"
        self.base_prompt = [("system", "You are a helpful personal assistant that helps the user with all their tasks and requests.")]

    def run(self, prompt: str):
        """
        A function that prompts the language model the given string and prints the response.
        """
        # messages = [("system", self.base_prompt + " This is their requst: " + prompt),
                    # ]
        # ai_msg = self.llm.invoke(messages)
        ai_msg = self.llm.invoke({"input": "{prompt}", "chat_history": self.read_chat_history()})

        self.save_chat_history(prompt, ai_msg.content)
        print(ai_msg.content)

    def read_chat_history(self) -> None:
        with open(self.chat_history_path, "r") as f:
            content = json.load(f)
            data = content["chat_history"]
            history = []
            for entry in data:
                history.append(HumanMessage(entry["Human"]))
                history.append(AIMessage(entry["AI"]))
            return history

    def save_chat_history(self, Humanmessage, AImessage) -> None:
        with open(self.chat_history_path, "r") as f:
            content = json.load(f)
            data = content["chat_history"]
            new_entry = {"Human": Humanmessage, "AI": AImessage}
            data.append(new_entry)
        with open(self.chat_history_path, "w") as f:
            json.dump(content, f)

agent = JarvisAgent()
agent.run("Can you help me with my homework?")
# agent.read_chat_history()
# agent.save_chat_history("Can you help me with my homework?", "Sure, what do you need help with?")
# agent.read_chat_history()
        
        

    
        
    


agent = JarvisAgent()
# agent.run("Can you help me with my homework?")
# agent.run("What did I say in the previous prompt?")
agent.read_chat_history()


# messages = [
#     (
#         "system",
#         "You are a helpful personal assistant that helps the user with all their tasks and requests.",
#     ),
# ]
# ai_msg = llm.invoke(messages)
# print(ai_msg.content)