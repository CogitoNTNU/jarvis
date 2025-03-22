from graph.graphstate import GraphState
from agents.model import Model
from agents.agent import Agent
from agents.model import Model, LLMType
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal
from tools.tools import get_tools, get_perplexity_based_tools, calendar_based_tools, get_other_tools

class Node:
    def __init__(self):
        self.simple_agent = Agent(model=Model.gpt_4o_mini).get_llm()
        self.tool_agent = self.simple_agent.bind_tools(get_tools())
        self.ok_agent = Agent(model=Model.gpt_4o).get_llm()
        self.ok_tool_agent = self.ok_agent.bind_tools(get_tools())
        

    def jarvis_agent(self, state: GraphState):
        """Agent to determine how to answer user question"""
        prompt = PromptTemplate(
            template= """
           You will act as a strict and reliable AI that ensures a response is always generated. Your primary function is to determine if a given task requires additional information or if it can be responded to directly.

            Follow these rules with absolute commitment:

            1.    Never respond with an empty string under any circumstance. The output must always be either 'use_tool' or 'generate'.
            2.    If the provided task requires external tools or additional information, respond with 'use_tool'.
            3.    If any tool has already been called and sufficient data is available, transition to 'generate'. Do not stay stuck on 'use_tool'.
            4.    Do not deviate from these two possible outputs. Any response must strictly adhere to this binary choice.
            5.    If uncertain, check the most recent tool decisions. If at least one tool decision (calendar_decision, perplexity_decision, or other_decision) has provided useful data, default to 'generate'.

            Here is the information provided for decision-making:

                Previous messages: {messages}
                Accumulated Data: {data}
                Calendar Decision: {calendar_decision}
                Perplexity Decision: {perplexity_decision}
                Other Tool Decision: {other_decision}

            If enough information has been gathered from already called tools, immediately transition to 'generate'.

            Again, under no circumstances should the output be an empty string. Failure to comply will result in disappointment. Stay consistent, and always provide a response.
                    """,
        )
        chain = prompt | self.ok_tool_agent | StrOutputParser()
        response = chain.invoke({
            "messages": state.get("messages", []),
            "data": state.get("data", {}),
            "calendar_decision": state.get("calendar_decision", {}),
            "perplexity_decision": state.get("perplexity_decision", {}),
            "other_decision": state.get("other_decision", {}),
            })
        response = response.replace("'", "").replace('"', "")
        return {"tool_decision": response}

    def tool_agent_decider(self, state: GraphState):
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

        chain = prompt | self.simple_agent | StrOutputParser()
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

    def router(self, state: GraphState) -> Literal["generate", "use_tool"]:
        """Router to determine what to do"""
        return state["tool_decision"]

    def agent_router(self, state: GraphState) -> Literal["perplexity", "calendar", "other"]:
        """Router to determine which agent to use"""
        return state["agent_decision"]

    def response_generator(self, state: GraphState):
        """Agent that generates a response to user based on user request 
        and possible data from tool calls"""
        prompt = PromptTemplate(
            template= """
            You are a personal assistant and your job is to generate a response to the user. 
           
            Here are the previous messages:
            
            Message: {messages}

            Here is the data currently accumulated: 

            Data: {data}


            Formulate a response that answer the users question and is formatted correctly
            """,

            #You should format the response so that it is easy for an text-to-speech model
            #to communicate to the user. 

        )
        chain = prompt | self.simple_agent
        response = chain.invoke({"messages": state["messages"], "data": state.get("data", {})})
        return {"messages": [response]}

    def perplexity_agent(self, state: GraphState):
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
        chain = prompt | self.simple_agent.bind_tools(get_perplexity_based_tools())
        response = chain.invoke({
            "messages": state["messages"], "data": state.get("data", {})})
        return {"messages": [response]}

    def calendar_decision_agent(self, state: GraphState):
        """Agent that decides what to do with the calendar"""
        prompt = PromptTemplate(
            template= """
            Your job is to determine which calendar-related tools are needed to answer the Jarvis agent’s question. You must respond with only the name of the appropriate option.

            Follow these rules with strict commitment:

            1.    If the user requests calendar information, you must decide whether to read or create an event.
            2.    If a calendar event is not found, create a new event.
            3.    If you have already searched for calendar events at least once, you should return to Jarvis instead of searching again.
            4.    If you have already created a calendar event, do not create it again—simply return to Jarvis.
            5.    Always provide an answer—never leave the response blank.

            Here is the information provided for decision-making:

                Previous Messages: {messages}
                Accumulated Data: {data}
                previous calendar decision: {calendar_decision}

            Your available options:

                use_calendar_tool → Call on calendar tools to retrieve or create events.
                return_to_jarvis → Return to the Jarvis agent after the necessary calendar action has been performed.

            You must strictly answer with only the option name—nothing else. Do not use quotes (' or ").
            """,
        )
        chain = prompt | self.ok_agent.bind_tools(calendar_based_tools()) | StrOutputParser()
        response = chain.invoke({
            "messages": state["messages"], "data": state.get("data", {}), "calendar_decision": state.get("calendar_decision", {})})
        response.replace("'", "")
        response.replace('"', '')
        return {"calendar_decision": response}

    def calendar_tool_decider(self, state: GraphState):
        """Agent that handles all actions in the calendar"""
        prompt = PromptTemplate(
            template= """
           Your job is to create and handle tool calls needed to create and read calendar events. You must determine the appropriate tools to use based on previous messages and accumulated data.

            Follow these rules with strict commitment:

            1.    Analyze previous messages and existing data to determine if a tool call is necessary.
            2.    If the user requested calendar information, decide whether to read or create an event.
            3.    If an event has already been searched for or created, avoid redundant tool calls.
            4.    Use previous calendar decisions to prevent unnecessary tool requests.
            5.    Always decide what tools to use and add them to additional_kwargs in the AI message.

            Here is the information provided for decision-making:

                Previous Messages: {messages}
                Accumulated Data: {data}
                Previous Calendar Decision: {calendar_decision}

            Your task:

                Determine the necessary tools to help the user.
                Ensure that tool calls are efficient and not duplicated.
                Add the selected tool calls to additional_kwargs in the AI message.
            """,
        )
        chain = prompt | self.ok_agent.bind_tools(calendar_based_tools())
        response = chain.invoke({"messages": state["messages"], "data": state.get("data", {}), "calendar_decision": state.get("calendar_decision", {})})
        return {"messages": response}

    def calendar_router(self, state: GraphState) -> Literal["use_calendar_tool", "return_to_jarvis"]:
        """Router to determine what to do"""
        return state["calendar_decision"]

    def other_agent(self, state: GraphState):
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
        chain = prompt | self.simple_agent.bind_tools(get_other_tools())
        response = chain.invoke({
            "messages": state["messages"], "data": state.get("data", {})})
        return {"messages": [response]}
