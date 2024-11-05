from graphstate import GraphState
from Agents.simpleagent import SimpleAgent, ToolsAgent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal
from tools.tools import get_tools, get_perplexity_based_tools, calender_based_tools, get_other_tools


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

def tool_agent_decider(state: GraphState):
    """Agent to determine what tool to use"""
    prompt = PromptTemplate(
        template= """
        Your job is to decide which Agent that should answer the users question.
        Answer only with the name of the agent you want to use.

        Here are the previous messages:
        
        Message: {messages}

        Here is the data currently accumulated: 

        Data: {data}

        Your options for agents are the following:
        1. 'perplexity': This agent has access to tools that use the perplexity API. 
                         These tools are the following: {perplexity_tools}
        2. 'calender':   This agent has access to calender tools
                         These tools are the following: {calender_tools}
        3. 'other':      Other tools available: {other_tools}
        """,
    )

    chain = prompt | SimpleAgent.llm
    response = chain.invoke({
        "messages": state["messages"], 
        "data": state.get("data", {}),
        "perplexity_tools": get_perplexity_based_tools(),
        "calender_tools": calender_based_tools(),
        "other_tools": get_other_tools()
        })
    return {"messages": [response]}

def router(state: GraphState) -> Literal["use_tool", "generate"]:
    """Router to determine what to do"""
    return state["tool_decision"]

def tool_agent_router(state: GraphState) -> Literal["perplexity", "calendar", "other"]:
    """Router to determine which agent to use"""
    return state["agent_decision"]

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

def perplexity_agent(state: GraphState):
    """Agent that handles tools using the perplexity api"""
    prompt = PromptTemplate(
        template= """
        Your job is to create tool_calls to tools using the perplexity API.
        The tool or tools you decide
        to call should help answer the users question.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Please decide what tools to use to help the user and
        add them to the additional_kwargs in the AI_message
        """,
    )
    chain = prompt | SimpleAgent.llm.bind_tools(get_perplexity_based_tools())
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}


def calender_desicion_agent(state: GraphState):
    """Agent that decides what to do with the calender"""
    prompt = PromptTemplate(
        template= """
        Your job is to determine if you wich calender related tools you need to answer the
        jarvis agents question and answer with only the name of the option
        choose.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Your options are the following:
        1. 'use_calendar_tool': Call on calendar_tools to help solve the users problem
        2. 'return_to_jarvis': go back to the jarvis agent

        Answer with the option name and nothing else.
        """,
    )
    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    return {"tool_decision": response}

def calender_tool_decider(state: GraphState):
    """Agent that handles all actions in the calender"""
    prompt = PromptTemplate(
        template= """
        Your job is to create and handle the tool calls needed to create and read calender events.
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        
        Please decide what tools to use to help the user and
        add them to the additional_kwargs in the AI_message
        """,
    )
    chain = prompt | SimpleAgent.llm.bind_tools(calender_based_tools()) | StrOutputParser()
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": response}


def calendar_router(state: GraphState) -> Literal["use_calendar_tool", "return_to_jarvis"]:
    """Router to determine what to do"""
    return state["tool_decision"]