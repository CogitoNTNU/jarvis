import openai

# For manual embedding of files.
# Chroma is used by Jarvis, but if for any reason you need manual embedding, this lib can help.

# For local embeddings in norwegian, see
# https://huggingface.co/ltg/norbert3-large and its sibling models
# Also check out the leaderboard for multilingual (not all languages) models: https://huggingface.co/spaces/mteb/leaderboard
def embed_note(text: str, use_openai: bool):
    if not isinstance(use_openai, bool):
        raise ValueError("use_openai must be True or False")

    if(use_openai):
        # Use OpenAI model
        embedding = openai.embeddings.create(
            input=text,
            model="text-embedding-ada-002",
            encoding_format=float
        )
        return embedding
    else:
        raise NotImplementedError("Local embedding models are not yet implemented")
        # TODO: Implement local models. Look at norwegian models
