import os, json, tiktoken, faiss
from datetime import datetime
import numpy as np
from openai import OpenAI

from typing import List, Tuple, Dict

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
EMBEDDING_DIMENSION = 3072
INDEX_FILE = "faiss_index.bin"
MAPPING_FILE = "id_to_metadata.json"
USER_VECTOR_MAP_FILE = "user_to_vector_ids.json"
EMBEDDING_MODEL = "text-embedding-3-large"

def create_or_load_index() -> faiss.IndexIDMap2:
    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)
        if not isinstance(index, faiss.IndexIDMap2):
            index = faiss.IndexIDMap2(index)
        return index
    base_index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
    return faiss.IndexIDMap2(base_index)

def load_id_to_metadata() -> Dict[str, Dict]:
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_user_to_vector_ids() -> Dict[str, List[int]]:
    if os.path.exists(USER_VECTOR_MAP_FILE):
        with open(USER_VECTOR_MAP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_index(index):
    faiss.write_index(index, INDEX_FILE)

def save_id_to_metadata(mapping: Dict[str, Dict]):
    with open(MAPPING_FILE, 'w') as f:
        json.dump(mapping, f)

def save_user_to_vector_ids(user_vector_map: Dict[str, List[int]]):
    with open(USER_VECTOR_MAP_FILE, 'w') as f:
        json.dump(user_vector_map, f)

def embed_and_store(text: str, user_id: str):
    index = create_or_load_index()
    id_to_metadata = load_id_to_metadata()
    user_to_vector_ids = load_user_to_vector_ids()
    
    embedding = get_embedding(text)
    vector_id = len(id_to_metadata)
    
    # Encode user_id into vector_id (e.g., high bits for user, low bits for vector)
    encoded_id = encode_user_vector_id(user_id, vector_id)
    
    index.add_with_ids(np.array([embedding], dtype=np.float32), np.array([encoded_id]))
    current_date = datetime.now().strftime("%Y-%m-%d")
    id_to_metadata[str(encoded_id)] = {"user_id": user_id, "text": f"Samtale fra {current_date}:\n{text}"}
    
    user_to_vector_ids.setdefault(user_id, []).append(encoded_id)
    
    save_index(index)
    save_id_to_metadata(id_to_metadata)
    save_user_to_vector_ids(user_to_vector_ids)

def encode_user_vector_id(user_id: str, vector_id: int) -> int:
    # Simple encoding: hash user_id and shift to make space for vector_id
    user_hash = int.from_bytes(user_id.encode('utf-8'), 'little') & 0xFFFFFFFF
    return (user_hash << 32) | vector_id

def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(
        input=f"{text}",

        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def similarity_search(query: str, user_id: str, k: int = 2) -> List[Tuple[str, float]]:
    index = create_or_load_index()
    id_to_metadata = load_id_to_metadata()
    user_to_vector_ids = load_user_to_vector_ids()
    
    if user_id not in user_to_vector_ids or not user_to_vector_ids[user_id]:
        return []
    
    user_ids = np.array(user_to_vector_ids[user_id], dtype=np.int64)
    
    if index.ntotal == 0:
        return []
    
    query_embedding = get_embedding(query)
    
    # Create a temporary index for the user's vectors
    temp_index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
    user_embeddings = []
    for vid in user_to_vector_ids[user_id]:
        vec = index.reconstruct(vid)
        user_embeddings.append(vec)
    user_embeddings = np.array(user_embeddings).astype('float32')
    temp_index.add(user_embeddings)
    
    distances, indices = temp_index.search(np.array([query_embedding], dtype=np.float32), k)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        encoded_id = user_to_vector_ids[user_id][idx]
        metadata = id_to_metadata.get(str(encoded_id))
        if metadata:
            similarity = 1 / (1 + dist)
            results.append((metadata["text"], similarity))
    
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
    user_id = "10011"  # Example user ID
    
    # Embed and store some texts
    embed_and_store("The stars twinkle brightly in the night sky.", user_id)
    embed_and_store("Cooking is an art that brings people together.", user_id)
    embed_and_store("Traveling opens your mind to new cultures and experiences.", user_id)


    # Perform similarity search
    query = "What is cooking?"
    results = similarity_search(query, user_id)
    
    print(f"Query: {query}")
    for text, similarity in results:
        print(f"Similarity: {similarity:.4f}")
        print(f"Text: {text}")
        print()