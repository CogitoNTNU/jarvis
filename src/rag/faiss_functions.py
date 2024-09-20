import os, json, tiktoken, faiss
import numpy as np
from openai import OpenAI
from typing import List, Tuple

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
EMBEDDING_DIMENSION = 3072
INDEX_FILE_TEMPLATE = "faiss_index_{user_id}.bin"
MAPPING_FILE_TEMPLATE = "id_to_text_{user_id}.json"
EMBEDDING_MODEL = "text-embedding-3-large"

def get_index_file_path(user_id: str) -> str:
    return INDEX_FILE_TEMPLATE.format(user_id=user_id)

def get_mapping_file_path(user_id: str) -> str:
    return MAPPING_FILE_TEMPLATE.format(user_id=user_id)

def create_or_load_index(user_id: str):
    index_path = get_index_file_path(user_id)
    if os.path.exists(index_path):
        return faiss.read_index(index_path)
    return faiss.IndexFlatL2(EMBEDDING_DIMENSION)

def load_id_to_text_mapping(user_id: str):
    mapping_path = get_mapping_file_path(user_id)
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r') as f:
            return json.load(f)
    return {}

def save_index(index, user_id: str):
    faiss.write_index(index, get_index_file_path(user_id))

def save_id_to_text_mapping(mapping, user_id: str):
    with open(get_mapping_file_path(user_id), 'w') as f:
        json.dump(mapping, f)

def embed_and_store(text: str, user_id: str):
    index = create_or_load_index(user_id)
    id_to_text = load_id_to_text_mapping(user_id)
    
    embedding = get_embedding(text)
    vector_id = len(id_to_text)
    
    index.add(np.array([embedding], dtype=np.float32))
    id_to_text[str(vector_id)] = text
    
    save_index(index, user_id)
    save_id_to_text_mapping(id_to_text, user_id)

def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def similarity_search(query: str, user_id: str, k: int = 2) -> List[Tuple[str, float]]:
    index = create_or_load_index(user_id)
    id_to_text = load_id_to_text_mapping(user_id)
    
    if index.ntotal == 0:
        return []
    
    query_embedding = get_embedding(query)
    
    distances, indices = index.search(np.array([query_embedding], dtype=np.float32), k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        if idx != -1:
            text = id_to_text.get(str(idx), "")
            similarity = 1 / (1 + distances[0][i])
            results.append((text, similarity))
    
    return results

def split_text_into_chunks(text: str, min_tokens: int = 200, model: str = EMBEDDING_MODEL) -> List[str]:
    tokenizer = tiktoken.encoding_for_model(model)
    
    chunks = []
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
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
    user_id = "user_123"  # Example user ID
    
    # Embed and store some texts
    #embed_and_store("The quick brown fox jumps over the lazy dog.", user_id)
    #embed_and_store("Python is a versatile programming language.", user_id)
    #embed_and_store("Machine learning is a subset of artificial intelligence.", user_id)

    # Perform similarity search
    query = "Hva er ki-strategi?"
    results = similarity_search(query, user_id)
    
    print(f"Query: {query}")
    for text, similarity in results:
        print(f"Similarity: {similarity:.4f}")
        print(f"Text: {text}")
        print()
