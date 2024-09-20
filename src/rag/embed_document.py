from faiss_functions import split_text_into_chunks, embed_and_store

#load text from ki-strategi.md
with open('src/rag/ki_strategi.md', 'r', encoding='utf-8') as file:
    text = file.read()

#split text into chunks
chunks = split_text_into_chunks(text)

print(f"Total chunks: {len(chunks)}")

#embed and store chunks
for i, chunk in enumerate(chunks, 1):
    embed_and_store(chunk)
    print(f"Chunk {i} stored: \n{chunk}\n")

"""
#print first 10 chunks
for i, chunk in enumerate(chunks[:10], 1):
    print(f"Chunk {i}:\n{chunk}\n")
"""