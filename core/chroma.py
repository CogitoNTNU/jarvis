import chromadb
import embedding # Embedding functions

# Chroma will connect to a chroma-database-server running in docker.
# Chroma can be run locally, but is not in Jarvis.
# Chroma handles embeddings by default, but we're customizing the model it uses.

async def init_chroma():
    chroma_client = await chromadb.AsyncHttpClient(host="chroma_db", port=8000)
    return chroma_client

async def create_collection(collection_name: str, chroma_client):
    collection = await chroma_client.create_collection(name="my_collection")
    return collection

async def add_document(text: str, id: str, collection):
    await collection.add(
        documents=[text],
        ids=[id]
    )

async def upsert_document(text: str, id: str, collection):
    await collection.upsert(
        documents=[text],
        ids=[id]
    )