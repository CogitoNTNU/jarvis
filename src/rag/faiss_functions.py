import os, json, tiktoken, faiss
import numpy as np
from openai import OpenAI
from typing import List, Tuple

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
EMBEDDING_DIMENSION = 3072
INDEX_FILE_PATH = "faiss_index.bin"
MAPPING_FILE_PATH = "id_to_text.json"
EMBEDDING_MODEL = "text-embedding-3-large"

def create_or_load_index():

    if os.path.exists(INDEX_FILE_PATH):
        return faiss.read_index(INDEX_FILE_PATH)
    return faiss.IndexFlatL2(EMBEDDING_DIMENSION)

def load_id_to_text_mapping():

    if os.path.exists(MAPPING_FILE_PATH):
        with open(MAPPING_FILE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_index(index):

    faiss.write_index(index, INDEX_FILE_PATH)

def save_id_to_text_mapping(mapping):

    with open(MAPPING_FILE_PATH, 'w') as f:
        json.dump(mapping, f)

def get_embedding(text: str) -> List[float]:

    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def embed_and_store(text: str):

    index = create_or_load_index()
    id_to_text = load_id_to_text_mapping()
    
    embedding = get_embedding(text)
    vector_id = len(id_to_text)
    
    index.add(np.array([embedding], dtype=np.float32))
    id_to_text[str(vector_id)] = text
    
    save_index(index)
    save_id_to_text_mapping(id_to_text)

def similarity_search(query: str, k: int = 2) -> List[Tuple[str, float]]:

    index = create_or_load_index()
    id_to_text = load_id_to_text_mapping()
    
    query_embedding = get_embedding(query)
    
    distances, indices = index.search(np.array([query_embedding], dtype=np.float32), k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:  # FAISS returns -1 for empty slots
            text = id_to_text[str(idx)]
            similarity = 1 / (1 + distances[0][i])  # Convert distance to similarity score
            results.append((text, similarity))
    
    return results

def split_text_into_chunks(text: str, min_tokens: int = 200, model: str = EMBEDDING_MODEL) -> List[str]:
    # Initialize the tokenizer
    tokenizer = tiktoken.encoding_for_model(model)
    
    chunks = []
    
    # Split the text into paragraphs
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # Split paragraph into lines
        lines = paragraph.split('\n')
        current_chunk = ""
        current_tokens = 0
        
        for line in lines:
            current_chunk += line + "\n"
            current_tokens = len(tokenizer.encode(current_chunk))
            
            if current_tokens >= min_tokens:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0
        
        if current_chunk:
            if chunks:
                chunks[-1] += current_chunk.strip()
            else:
                chunks.append(current_chunk.strip())
    
    return chunks

# Example usage
if __name__ == "__main__":
    # Embed and store some texts
    #embed_and_store("The quick brown fox jumps over the lazy dog.")
    #embed_and_store("Python is a versatile programming language.")
    #embed_and_store("Machine learning is a subset of artificial intelligence.")

    # Perform similarity search
    query = "Hva er ki-strategi?"
    results = similarity_search(query)
    
    print(f"Query: {query}")
    for text, similarity in results:
        print(f"Similarity: {similarity:.4f}")
        print(f"Text: {text}")
        print()
