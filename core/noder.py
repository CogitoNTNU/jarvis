from graphstate import GraphState
from Agents.simpleagent import SimpleAgent
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


def jarvis_agent(state: GraphState):
    """Agent to determine how to answer user question"""
    prompt = PromptTemplate(
        template= """
        Lorem ipsum....
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        TODO: Create options for the llm to answer

        Answer with the option name and nothing else
        """,
    )
    chain = prompt | SimpleAgent.llm | StrOutputParser()

    return chain.invoke({"messages": state["messages"], "data": state.get("data", {})})

def tool_decider(state: GraphState):
    """Agent to determine what tool to use"""
    prompt = PromptTemplate(
        template= """
        Lorem ipsum....
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        TODO: Create options for the llm to answer

        Answer with the option name and nothing else
        """,
    )

    chain = prompt | SimpleAgent.llm | StrOutputParser()

    return chain.invoke({"messages": state["messages"], "data": state.get("data", {})})

def response_generator(state: GraphState):
    """Agent that generates a response to user based on user request 
    and possible data from tool calls"""
    #TODO Implement
    return ""