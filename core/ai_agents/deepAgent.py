from typing import Annotated
from typing_extensions import TypedDict
import os

from fastapi.websockets import WebSocket

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ai_agents.WebSocketAgent import WebSocketAgent
from ai_agents.model import Model
from tools.tools import get_tools  # samler alle verktøy i ett kall

class DeepResearchNeoAgent(WebSocketAgent):
    """Neo‑stil agent som også kjører dybde‑verifisering."""

    # --- konfig -------------------------------------------------------------
    system_prompt = (
        "You are Jarvis‑Deep, an AI assistant focused on thorough, multi‑perspective research. "
        "When you answer, be concise in wording but rich in content. If a tool helps, call it."
    )
    model_name: str = Model.gpt_4_1[0]
    temperature: float = 0.0
    max_tokens: int = 32000
    

    # ---------------------------------------------------------------------
    def __init__(self):
        print("Instantiated DeepResearchNeoAgent …")

        # 1) Modell + verktøy
        llm = ChatOpenAI(model=self.model_name,
                          temperature=self.temperature,
                          max_tokens=self.max_tokens)
        tools = get_tools()
        tool_node = ToolNode(tools)
        llm_with_tools = llm.bind_tools(tools)

        # ---- interne node‑funksjoner -----------------------------------
        class _State(TypedDict):
            messages: Annotated[list, add_messages]

        # a) Samle dybde‑svar (kan trigge verktøy)
        def deep_research(state: _State):
            if not state["messages"]:
                state["messages"] = [SystemMessage(content=self.system_prompt)]
            answer = llm_with_tools.invoke(state["messages"])
            return {"messages": [answer]}

        # b) Verifiser dybde – forbedre hvis nødvendig
        verify_prompt = (
            "Your job is to analyse if the following assistant answer represents deep research.\n"
            "Return only the word ‘Deep’ if it meets the criteria, otherwise return ‘Shallow’."
        )
        improve_prompt = (
            "The previous answer was shallow. Rewrite it to be deeper, include more perspectives, "
            "logical structure and detailed explanations.\n\nOriginal answer: {text}"
        )

        def verify_depth(state: _State):
            last_msg = state["messages"][-1]
            judge = llm.invoke([
                SystemMessage(content=verify_prompt),
                AIMessage(content=last_msg.content)
            ]).content.strip()

            if judge.startswith("Shallow"):
                improved = llm.invoke([
                    SystemMessage(content=improve_prompt.format(text=last_msg.content))
                ])
                return {"messages": [AIMessage(content=improved.content)]}
            else:
                # svar var dypt nok – returner uendret
                return {"messages": [last_msg]}

        # ---- bygg graf --------------------------------------------------
        gb = StateGraph(_State)
        gb.add_node("deep_research", deep_research)
        gb.add_node("verify_depth", verify_depth)
        gb.add_node("tools",  tool_node)

        gb.add_edge(START, "deep_research")
        gb.add_edge("deep_research", "verify_depth")
        gb.add_conditional_edges("verify_depth", tools_condition)
        gb.add_edge("tools", "verify_depth")
        gb.add_edge("verify_depth", END)

        gb.set_entry_point("deep_research")
        self.graph = gb.compile()

    # ------------------------------------------------------------------
    def stream_graph_updates(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)
