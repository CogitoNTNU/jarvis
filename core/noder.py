from graphstate import GraphState
from Agents.simpleagent import SimpleAgent, ToolsAgent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal
from tools.tools import get_tools, get_perplexity_based_tools, calendar_based_tools, get_other_tools


def jarvis_agent(state: GraphState):
    """Agent to determine how to answer user question"""
    prompt = PromptTemplate(
        template= """
        Your job is to determine if you need tools to answer the
        users question and answer with only the name of the option
        chosen. You have access to chat history using tools, thus also some personal data can be retrieved.
        som times you have to use multiple tools from multiple diffrent tools that has been called to complte the users requests.
        if you calender is sent to you for a second or third time you should generate instead of using tools.
        if you get a complex task you should call a tool to help you solve the task.
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Your options are the following:
        - 'use_tool': Call on tools to help solve the users problem
        - 'generate': Generate a response if you have what you need to answer

        Answer with the option name and nothing else there should not be any ' or " in the answer.
        You can never answer with an empty string.
        please never answer with an empty string.
        if you answer with an ampty string you will not do anything and stop working.
        """,
    )
    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    response.replace("'", "")
    response.replace('"', '')
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
        - "perplexity": This agent has access to tools that use the perplexity API and tools 
                        for doing a chat history search. These tools are the following: {perplexity_tools}
        - "calendar":   This agent has access to calendar tools
                         These tools are the following: {calendar_tools}
        - "other":      Other tools available: {other_tools}


        Answer with the option name and nothing else there should not be any ' or " in the answer.
        """,
    )

    chain = prompt | SimpleAgent.llm | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], 
        "data": state.get("data", {}),
        "perplexity_tools": get_perplexity_based_tools(),
        "calendar_tools": calendar_based_tools(),
        "other_tools": get_other_tools()
        })
    response.replace("'", "")
    response.replace('"', '')
    return {"agent_decision": [response]}

def router(state: GraphState) -> Literal["generate", "use_tool"]:
    """Router to determine what to do"""
    return state["tool_decision"]

def agent_router(state: GraphState) -> Literal["perplexity", "calendar", "other"]:
    """Router to determine which agent to use"""
    return state["agent_decision"]

def response_generator(state: GraphState):
    """Agent that generates a response to user based on user request 
    and possible data from tool calls"""
    prompt = PromptTemplate(
        template= """
        You are a personal assistant and your job is to generate a response to the user. 
        You should format the response so that it is easy for an text-to-speech model
        to communicate to the user

        Here are the previous messages:
        
        Message: {messages}

        Here is the data currently accumulated: 

        Data: {data}

        Formulate a response that answer the users question and is formatted correctly
        """,
    )
    chain = prompt | SimpleAgent.llm
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}


def perplexity_agent(state: GraphState):
    """Agent that handles tools using the perplexity api"""
    prompt = PromptTemplate(
        template= """
        Your job is to create tool_calls to tools using the perplexity API or 
        to tools that do a RAG-search on the chat history. The tool or tools you decide
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


def calendar_decision_agent(state: GraphState):
    """Agent that decides what to do with the calendar"""
    prompt = PromptTemplate(
        template= """
        Your job is to determine if you which calendar related tools you need to answer the
        jarvis agents question and answer with only the name of the option
        choose.
        if you cant find a calendar event you should create a calendar event.
        you should create a claender event or read calendar events. if the user has asked for it.
        if you have searched for calendar events atleast once you should probably return to jarvis.
        the same is for creatting a event, you only need to create that event once. and return to jarvis.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Your options are the following:
        - 'use_calendar_tool': Call on calendar_tools to help solve the users problem
        - 'return_to_jarvis': go back to the jarvis agent

        Answer with the option name and nothing else there should not be any ' or " in the answer.
        """,
    )
    chain = prompt | ToolsAgent.agent | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    response.replace("'", "")
    response.replace('"', '')
    return {"calendar_decision": response}

def calendar_tool_decider(state: GraphState):
    """Agent that handles all actions in the calendar"""
    prompt = PromptTemplate(
        template= """
        Your job is to create and handle the tool calls needed to create and read calendar events.¨
        You will based on previous messages and data decide what tools to use. and create the tool calls.
        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        
        Please decide what tools to use to help the user and
        add them to the additional_kwargs in the AI_message
        """,
    )
    chain = prompt | SimpleAgent.llm.bind_tools(calendar_based_tools())
    response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
    return {"messages": response}


def calendar_router(state: GraphState) -> Literal["use_calendar_tool", "return_to_jarvis"]:
    """Router to determine what to do"""
    return state["calendar_decision"]

def other_agent(state: GraphState):
    """Agent that handles other tools available in the system"""
    prompt = PromptTemplate(
        template= """
        Your job is to create tool_calls to tools.
        The tool or tools you decide
        to call should help answer the users question.
        You can also use the chat history search tool to help answer the users question.

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        Please decide what tools to use to help the user and
        add them to the additional_kwargs in the AI_message
        """,
    )
    chain = prompt | SimpleAgent.llm.bind_tools(get_other_tools())
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    return {"messages": [response]}