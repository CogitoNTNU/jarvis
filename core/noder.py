from graphstate import GraphState
from Agents.simpleagent import SimpleAgent, ToolsAgent
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal


def jarvis_agent(state: GraphState):
    """Agent to determine how to answer user question"""
    prompt = PromptTemplate(
        template= """
        Your job is to determine if you need tools to answer the
        users question.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Your options are the following

        Answer with the option name and nothing else
        """,
    )
    chain = prompt | SimpleAgent.llm | StrOutputParser()

    return chain.invoke({"messages": state["messages"], "data": state.get("data", {})})

def tool_decider(state: GraphState):
    """Agent to determine what tool to use"""
    prompt = PromptTemplate(
        template= """
        Your job is to create tool_calls. The tool or tools you decide
        to call should help answer the users question.

        Here are the previous messages:
        
        Message: {messages}

        Here is the data currently accumulated: 

        Data: {data}

        Please decide what tools to use to help the user and
        add them to the additional_kwargs in the AI_message
        """,
    )

    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}

def router(state: GraphState) -> Literal["use_tools", "generate"]:
    """Router to determine what to do"""
    return state["decision"]

def response_generator(state: GraphState):
    """Agent that generates a response to user based on user request 
    and possible data from tool calls"""
    #TODO Implement
    return ""