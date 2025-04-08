# Premade tool imports
from langchain_core.tools import tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain_core.tools.structured import StructuredTool
# Custom tool imports
from core.chroma import add_document


#Tool to embed a PDF file and save it ti ChromaDB
@tool (name = "Embed PDF", description = "Embed a PDF file and save it to memory.")
async def embed_pdf(self, file_path: str): 
        loader =PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter =  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        texts = text_splitter.split_documents(documents)

        for i, text in enumerate(texts):
            await add_document(text.page_content, f"pdf_chunk_{i}", self.collection)
        return f"PDF '{file_path}' has been embedded and saved to memory."

def get_tool() -> StructuredTool:
      return embed_pdf
      