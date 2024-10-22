from langchain_openai import ChatOpenAI
from models import Model
from config import OPENAI_API_KEY


class SimpleAgent:
    llm = ChatOpenAI(
        model = Model.gpt_4o,
        temperature=0,
        max_tokens=512,
        )
