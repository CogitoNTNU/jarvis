class LLMType:
    chat_open_ai = "ChatOpenAI"

class Model:
    # OpenAI models
    gpt_4o_mini: tuple[str, LLMType] = ("gpt-4o-mini", LLMType.chat_open_ai)
    gpt_4o: tuple[str, LLMType] = ("gpt-4o", LLMType.chat_open_ai)
    gpt_35: tuple[str, LLMType] = ("gpt-3.5-turbo", LLMType.chat_open_ai)
    gpt_o3_mini: tuple[str, LLMType] = ("o3-mini", LLMType.chat_open_ai)
