import tiktoken # To count tokens
from ai_agents.model import Model

"""
Functions to filter and trim the message history if it goes above the token limit.
TODO: Also functions to generally trim the message history to reduce token usage.
"""

# Counts tokens using the tiktoken native library from langchain. By default counts gpt4o tokens.
def count_tokens(messages, model=Model.gpt_4o_mini):
    encoding = tiktoken.encoding_for_model(model)
    # Tokenize each message in the history and sum up the token count
    total_tokens = 0
    for role, content in messages:
        total_tokens += len(encoding.encode(role))  # Count tokens for the role
        total_tokens += len(encoding.encode(content))  # Count tokens for the content
    return total_tokens

# Can trim history by removing a message at a time until within the specified token limit.
def trim_history(chat_history, max_tokens):
    current_tokens = count_tokens(chat_history)
    while current_tokens > max_tokens:
        chat_history.pop(0)  # Remove the oldest message
        current_tokens = count_tokens(chat_history)
    return chat_history