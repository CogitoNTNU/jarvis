from langchain_openai import ChatOpenAI
from models import Model
from config import OPENAI_API_KEY
from tools.tools import get_tools


class SimpleAgent:
    llm = ChatOpenAI(
        model = Model.gpt_4o,
        temperature=0,
        max_tokens=1024,
        )
    
class ToolsAgent:
    agent = SimpleAgent.llm.bind_tools(get_tools())
