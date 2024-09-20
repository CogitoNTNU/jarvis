from __future__ import annotations

import os
from typing import Literal, TypedDict

from chromadb import Client
from dotenv import load_dotenv
from requests import Response, post


class Message(TypedDict):
    role: Literal["user", "system", "assistant"]
    content: str


def userMessage(message: str) -> Message:
    return {"role": "user", "content": message}


def AIMessage(message: str) -> Message:
    return {"role": "assistant", "content": message}


def SystemMessage(message: str) -> Message:
    return {"role": "system", "content": message}


class Memory:
    _chroma = Client()
    _chat_history = _chroma.create_collection("chat_history")
    _llm: LLM
    _id: int = 0

    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    def add(self, info: str) -> None:
        # Summarize conversation
        summary = self._llm.send_messages(
            [
                SystemMessage(
                    f"You are a part of a RAG system and you'r purpose is to summarize information given by the user. Given the following statement from the user, return a list of all interesting information given to us by the user. If there is nothing interestiong to summarize write exactly 'NO_INFO'. ONLY use information provided in the following statement. Statement: {info}"
                )
            ]
        )

        if summary == "NO_INFO":
            return

        # DEBUG
        print(f"\n=======SUMMARY=======\n{summary}\n======SUMMARY=======\n")

        # Add summary to chromadb
        self._chat_history.add(ids=[f"doc{self._id}"], documents=[summary])
        self._id += 1

    def search(self, prompt: str):
        return self._chat_history.query(query_texts=[prompt], n_results=3)


class LLM:
    __API_KEY: str
    __ENDPOINT: str = "https://api.openai.com/v1/chat/completions"
    __MODEL: str
    _memory: Memory
    _history: list[Message]

    def __init__(self, API_KEY: str, MODEL: str = "gpt-4o-mini") -> None:
        self.__API_KEY = API_KEY
        self.__MODEL = MODEL
        self._memory = Memory(self)
        self._history = []

    def _post(self, messages: list[Message]) -> Response:
        return post(
            self.__ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.__API_KEY}",
            },
            json={
                "model": self.__MODEL,
                "messages": messages,
            },
        )

    def send_messages(self, messages: list[Message]) -> str:
        return self._post(messages).json()["choices"][0]["message"]["content"]

    def ask(self, question: str) -> str:
        user_question = userMessage(question)

        # Get context
        context = self._memory.search(question)["documents"]
        context = [] if context is None else context[0]

        # DEBUG
        print(f"\n=======CONTEXT=======\n{context}\n======CONTEXT=======\n")

        # Craft ai prompt
        messages = [
            SystemMessage(
                f"You are an assistant for question-answering tasks. Use the following pieces of retrieved context and previous conversation to answer the question. If you don't know the answer, say that you don't know. Context: {context}, Conversation: {self._history}"
            ),
            user_question,
        ]

        # Get llm answer
        answer = self.send_messages(messages)

        # Delete oldest messages if neccessary
        if len(self._history) >= 9:
            self._history = self._history[2:]

        # Add newest messages to history
        self._history.append(user_question)
        self._history.append(AIMessage(answer))

        # Add new information to memory
        self._memory.add(question)

        return answer


if __name__ == "__main__":
    load_dotenv()
    llm = LLM(os.environ["OPENAI_API_KEY"])

    while (question := input("\n\n> ")) != "q":
        print(llm.ask(question))
