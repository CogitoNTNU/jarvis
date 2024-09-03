from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=OPENAI_API_KEY,  # if you prefer to pass api key in directly instaed of using env vars
    # base_url="...",
    # organization="...",
    # other params...
)


base_prompt = "You are a helpful personal assistant that helps the user with all their tasks and requests. This is their request: "
def run(prompt: str):
    messages = [("system", base_prompt+ prompt)]
    ai_msg = llm.invoke(messages)
    print(ai_msg.content)

run("Can you help me with my homework?")

# messages = [
#     (
#         "system",
#         "You are a helpful personal assistant that helps the user with all their tasks and requests.",
#     ),
# ]
# ai_msg = llm.invoke(messages)
# print(ai_msg.content)