import re
from graph.graphstate import GraphState, CalendarGraphState
from ai_agents.model import Model
from ai_agents.agent import Agent
from ai_agents.model import Model, LLMType
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal, Union, Dict, Any
from tools.tools import get_tools, get_perplexity_based_tools, calendar_based_tools, get_other_tools
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

class Node:
    def __init__(self):
        self.gpt_4o_mini = Agent(model=Model.gpt_4o_mini).get_llm()
        self.gpt_4o_mini_tool = self.gpt_4o_mini.bind_tools(get_tools())
        self.gpt_o4_mini = Agent(model=Model.gpt_o4_mini).get_llm()
        self.gpt_o4_mini_tool = self.gpt_o4_mini.bind_tools(get_tools())
        self.gpt_4o_mini_low_temp = Agent(model=Model.gpt_4o_mini, override_temp=0.1).get_llm()
        self.calendar_available = False

    # Helper method to extract content from various message types
    def get_message_content(self, message):
        """
        Extract content from a message, whether it's a dict or a Message object.
        """
        if isinstance(message, (HumanMessage, AIMessage, SystemMessage, BaseMessage)):
            # It's a langchain Message object
            return message.content
        elif isinstance(message, dict):
            # It's a dictionary
            return message.get("content", "")
        else:
            # Unknown type - return empty string
            print(f"Warning: Unknown message type: {type(message)}")
            return ""

    def jarvis_agent(self, state: GraphState):
        """Agent to determine how to answer user question"""
        prompt = PromptTemplate(
            template= """
       You will act as a strict and reliable AI that ensures the correct decision is made about using tools.

        Follow these rules with absolute commitment:

        1. Never respond with an empty string. The output must always be either 'use_tool' or 'generate'.
        
        2. ALWAYS respond with 'use_tool' when:
            - The request involves complex abilities outside of your simple knowledge and text generation
            - The request involves calendar actions (create, add, schedule, remind, appointment, meeting, event)
            - The request requires searching for information online
            - The request asks for data that isn't in the conversation history
           
        3. Only respond with 'generate' when:
           - Sufficient data has already been collected by tools
           - The request is a simple greeting or conversation
           - The question can be answered with information already present
           
        4. When in doubt, default to 'use_tool' - it's better to gather more information than to generate an incomplete response.
        
        5. If tools have already been used and provided useful data, then choose 'generate'.

        Check available tools that can be called: {available_tools}
        
        Here is the information for decision-making:
            Previous messages: {messages}
            Accumulated Data: {data}
            Perplexity Decision: {perplexity_decision}
            Other Tool Decision: {other_decision}
            Calendar Events: {calendar_events}

        Again, any request involving calendar operations MUST use tools.
                """,
        )
        chain = prompt | self.gpt_o4_mini| StrOutputParser()
        
        # Collect all available tools
        available_tools = {
            "Perplexity Tools": get_perplexity_based_tools(),
            "Calendar Tools": calendar_based_tools(),
            "Other Tools": get_other_tools()
        }
        
        response = chain.invoke({
            "available_tools": available_tools,
            "messages": state.get("messages", []),
            "data": state.get("data", {}),
            "calendar_events": state.get("calendar_events", {}),
            "perplexity_decision": state.get("perplexity_decision", {}),
            "other_decision": state.get("other_decision", {}),
            })
        response = response.replace("'", "").replace('"', '')
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

        chain = prompt | self.gpt_o4_mini_tool | StrOutputParser()
        response = chain.invoke({
            "messages": state["messages"], 
            "data": state.get("data", {}),
            "perplexity_tools": get_perplexity_based_tools(),
            "calendar_tools": calendar_based_tools(),
            "other_tools": get_other_tools()
            })
        response = response.replace("'", "").replace('"', '')
        return {"agent_decision": [response]}

    def router(self, state: GraphState) -> str:
        """Router deciding next step after jarvis_agent."""
        # Get the tool_decision from state
        tool_decision = state.get("tool_decision", "")
        
        # Add logging
        print(f"Router checking tool_decision: '{tool_decision}'")
        
        # Validate the decision exists and is valid
        if tool_decision == "use_tool":
            return "use_tool"
        elif tool_decision == "generate":
            return "generate"
        else:
            # Default to generate if we have an invalid or missing decision
            print(f"WARNING: Invalid tool_decision '{tool_decision}', defaulting to 'generate'")
            return "generate"

    def agent_router(self, state: GraphState) -> str:
        """Router for deciding which agent to use."""
        # Extract the agent decision from state
        agent_decision = state.get("agent_decision", [])[0] if isinstance(state.get("agent_decision", []), list) else state.get("agent_decision", "")
        
        # Add logging
        print(f"Agent router received decision: '{agent_decision}'")
        
        # Ensure we return a valid option - always include calendar as a valid option
        valid_options = ["perplexity", "other", "calendar"]  # Always include calendar
        
        if agent_decision not in valid_options:
            print(f"WARNING: Invalid agent decision '{agent_decision}', defaulting to 'perplexity'")
            return "perplexity"
        
        return agent_decision

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
        chain = prompt | self.gpt_4o_mini_low_temp
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
        chain = prompt | self.gpt_4o_mini.bind_tools(get_perplexity_based_tools())
        response = chain.invoke({
            "messages": state["messages"], "data": state.get("data", {})})
        return {"messages": [response]}

    def calendar_decision_agent(self, state: CalendarGraphState):
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
                Accumulated Data: {calendar_data}
                previous calendar decision: {calendar_decision}
                calendar events : {calendar_events}

            Your available options:

                use_calendar_tool → Call on calendar tools to retrieve or create events.
                return_to_jarvis → Return to the Jarvis agent after the necessary calendar action has been performed.

            If you belive the task is satisfactory completed return to jarvis
            You must strictly answer with only the option name—nothing else. Do not use quotes (' or “).
            """,
        )
        chain = prompt | self.gpt_o4_mini | StrOutputParser()
        response = chain.invoke({
        "messages": state["messages"], 
        "calendar_data": state.get("calendar_data", {}),  # Use correct key from CalendarGraphState
        "calendar_decision": state.get("calendar_decision", {}),
        "calendar_events": state.get("calendar_events", {})  # Add calendar_events parameter
    })
        response = response.replace("'", "").replace('"', '')
        return {"calendar_decision": response}

    def calendar_tool_decider(self, state: CalendarGraphState):
        """Agent that handles all actions in the calendar"""
        prompt = PromptTemplate(
            template= """
        Your job is to create and handle tool calls needed to create and read calendar events. You must determine the appropriate tools to use based on previous messages and accumulated data.

        Follow these rules with strict commitment:

        1.    Analyze previous messages and existing data to determine if a tool call is necessary.
        2.    If the user requested calendar information, decide whether to read or create an event.
        3.    If an event has already been searched for or created, avoid redundant tool calls.
        4.    Use previous calendar decisions to prevent unnecessary tool requests.
        5.    Always decide what tools to use and add them to the additional_kwargs in the AI message.
        6.    IMPORTANT: Check the existing calendar_events to avoid creating duplicates.

        Here is the information provided for decision-making:

            Previous Messages: {messages}
            Accumulated Data: {calendar_data}
            Previous Calendar Decision: {calendar_decision}
            Existing Calendar Events: {calendar_events}

        Your task:

            Determine the necessary tools to help the user.
            Ensure that tool calls are efficient and not duplicated.
            Add the selected tool calls to additional_kwargs in the AI message.
            If not enough information is given add what you believe is most correct.
            DO NOT create an event that already exists in the calendar_events.
        """,
        )
        chain = prompt | self.gpt_4o_mini.bind_tools(calendar_based_tools())
        response = chain.invoke({
            "messages": state["messages"], 
            "calendar_data": state.get("calendar_data", {}),
            "calendar_decision": state.get("calendar_decision", {}),
            "calendar_events": state.get("calendar_events", {})
        })
        return {"messages": [response]}  # Wrap response in a list to maintain consistency

    def calendar_router(self, state: CalendarGraphState) -> str:
        """Router for deciding next step after calendar_tool_decider."""
        decision = state.get("calendar_decision", "")
        
        if not decision:
            print("No decision found, defaulting to calendar tool")
            return "use_calendar_tool"
        
        print(f"Calendar router analyzing decision: '{decision}'")
        
        # Simple direct check of the decision value
        if decision == "return_to_jarvis":
            print("Returning to Jarvis from calendar")
            return "return_to_jarvis"
        elif decision == "use_calendar_tool":
            print("Using calendar tool")
            return "use_calendar_tool"
        else:
            # Handle unexpected values
            print(f"Unexpected calendar decision '{decision}', defaulting to calendar tool")
            return "use_calendar_tool"
            
    def other_agent(self, state: GraphState):
        """Agent that handles other tools available in the system"""
        prompt = PromptTemplate(
            template= """
            Your job is to create tool_calls to tools.
            The tool or tools you decide to call should help answer the users question.
            You can also use the chat history search tool to help answer the users question.
            
            Here are previous messages:
            
            Message: {messages}

            Data currently accumulated: 
            
            Data: {data}

            Please decide what tools to use to help the user and
            add them to the additional_kwargs in the AI_message
            """,
        )
        chain = prompt | self.gpt_o4_mini.bind_tools(get_other_tools())
        response = chain.invoke({
            "messages": state["messages"], "data": state.get("data", {})})
        return {"messages": [response]}
