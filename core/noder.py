from graphstate import GraphState
from Agents.simpleagent import SimpleAgent, ToolsAgent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal
from tools.tools import get_tools
def jarvis_agent(state: GraphState):
    """Agent to determine how to answer user question"""
    prompt = PromptTemplate(
        template= """
        Your job is to determine if you need tools to answer the
        users question and answer with only the name of the option
        choose.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Your options are the following:
        1. 'use_tool': Call on tools to help solve the users problem
        2. 'generate': Generate a response if you have what you need to answer

        Answer with the option name and nothing else
        """,
    )
    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    return {"tool_decision": response}

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

    chain = prompt | ToolsAgent.agent
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}

def router(state: GraphState) -> Literal["use_tool", "generate"]:
    """Router to determine what to do"""
    return state["tool_decision"]

def response_generator(state: GraphState):
    """Agent that generates a response to user based on user request 
    and possible data from tool calls"""
    prompt = PromptTemplate(
        template= """
        You are a personal assistant and your job is to generate a response to the user. 

        Here are the previous messages:
        
        Message: {messages}

        Here is the data currently accumulated: 

        Data: {data}

        Formulate a response that answer the users question
        """,
    )
    chain = prompt | SimpleAgent.llm
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}



def calender_agent(state: GraphState):
    """Agent that handles all actions in the calender"""
    prompt = PromptTemplate(
        template= """
        Your job is to handle any calender events that the user requests.
        you have acces to the google calender api and can create, delete 

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        See calender events are in:
        
        Calendere evnts:{calender_events}

        Your options are the following:
        to generate a calender event
        Answer with the option name and nothing else
        """,
    )
    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {}), "calender_events": get_tools()[]})
    return {"tool_decision": response}
