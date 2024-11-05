from openai import OpenAI
import dotenv
import config
from graphstate import GraphState
from Agents.simpleagent import SimpleAgent, ToolsAgent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Literal
from tools.tools import calender_based_tools
dotenv.load_dotenv()


def calender_agent(state: GraphState):
    """Agent that handles all actions in the calender"""
    prompt = PromptTemplate(
        template= """
        Your job is to handle any calender tasks that the user requests.
        you have acces to the google calender api and can create, delete 

        Here are previous messages:
        
        Message: {messages}

        Data currently accumulated: 

        Data: {data}

        See calender events are in:
        
        Your options are the following:
        1. "read_calendar_continue": Read calender events and continue
        2. "read_calendar_loop"Read: calender event and loop back to this norde
        3. "create_calender_event: create calender event and continue
        
        Answer with the option name and nothing else!
        """,
    )
    chain = prompt | SimpleAgent.llm.bind_tools(calender_based_tools()) | StrOutputParser()
    response = chain.invoke({
        "messages": state["messages"], "data": state.get("data", {})})
    return {"tool_decision": response}
