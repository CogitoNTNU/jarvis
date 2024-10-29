from graphstate import GraphState
from Agents.simpleagent import SimpleAgent
from langchain.prompts import PromptTemplate


def jarvis_agent(state: GraphState):
    """Agent to determine how to answer user question"""
    promt = PromptTemplate(
        template= """
        Lorem ipsum....
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        TODO: Create options for the llm to answer

        Answer with the option name and nothing else
        """
    )