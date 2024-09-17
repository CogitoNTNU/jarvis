from langchain_openai import ChatOpenAI

class Agent:
    def __init__(self, model_type) -> None:
        self.llm = ChatOpenAI(
            model=model_type,
        )

    
