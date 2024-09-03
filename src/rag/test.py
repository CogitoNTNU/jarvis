import os

import bs4
from dotenv import load_dotenv
from langchain import hub
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# Initialize llm
llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])

# Load website as document
bs4_strainer = bs4.SoupStrainer(class_=("post-title", "post-header", "post-content"))
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs={"parse_only": bs4_strainer},
)
docs = loader.load()

# Split document into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200, add_start_index=True
)
chunks = text_splitter.split_documents(docs)

# Store chunk in vector database
vectorstore = Chroma.from_documents(chunks, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})

# Define RAG chain
rag_chain = (
    {
        "context": retriever
        | (lambda docs: "\n\n".join(doc.page_content for doc in docs)),
        "question": RunnablePassthrough(),
    }
    | hub.pull("rlm/rag-prompt")
    | llm
    | StrOutputParser()
)


while (prompt := input("\n\n> ")) != "q":
    for chunk in rag_chain.stream(prompt):
        print(chunk, end="", flush=True)
