from langchain_openai import ChatOpenAI
from Agents.model import Model, LLMType

class Agent:
    temperature = 0
    max_tokens = 2048
    model: Model
    llm_type: LLMType

    def __init__(self, model: Model):
        self.model = model
    
    def get_llm(self):
        if (self.model[1] == LLMType.chat_open_ai):
            self.llm = ChatOpenAI(
            model = self.model[0],
            temperature = self.temperature,
            max_tokens = self.max_tokens,
        )
            
        return self.llm

    

