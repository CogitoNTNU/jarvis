from openai import OpenAI
import dotenv
import config

dotenv.load_dotenv()

user_query = "Hvordan blir været i Trondheim i morgen?"

def get_perplexity_response(user_query):
    
    messages = [
        {
            "role": "user",
            "content": f"{user_query}\n\nPresenter informasjon som det skulle vært presentert muntlig.",
        },
    ]

    client = OpenAI(api_key=config.PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3.1-sonar-large-128k-online",
        messages=messages,
        temperature=0.0,
    )
    
    message = response.choices[0].message.content

    return message

print(get_perplexity_response(user_query))

# chat completion with streaming
"""
response_stream = client.chat.completions.create(
    model="llama-3.1-sonar-small-128k-online",
    messages=messages,
    stream=True,
)
for response in response_stream:
    if response.choices[0].delta.content is not None:
        print(response.choices[0].delta.content, end='')
print()  # Add a newline at the end
"""