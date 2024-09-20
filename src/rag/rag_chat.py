import os
from faiss_functions import similarity_search
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_response(query, context):
    messages = [
        {"role": "system", "content": "You are a helpful assistant. You will be given a context and a question. Your answer must solely be based on the context. If you don't know the answer, say so. Reply in Norwegian."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
    ]
    

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=5000
    )
    
    return response.choices[0].message.content.strip()

def rag_chat():
    while True:
        query = input("User: ")
        if query.lower() in ['exit', 'quit', 'bye']:
            print("Assistant: Goodbye!")
            break
        
        results = similarity_search(query)
        context = "\n\n".join([f"Context {i+1}:\n{text}" for i, (text, _) in enumerate(results)])
        
        response = generate_response(query, context)
        print("\n")
        print(f"Assistant: {response}")
        print("\n")

if __name__ == "__main__":
    rag_chat()