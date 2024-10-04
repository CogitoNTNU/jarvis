import os
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from PyPDF2 import PdfReader

# oh no, a pdf file, hide the children
@tool 
def read_pdf_file(file_path: str):
    """
    Use this tool to read the contents of a pdf file.
    The file path should be relative to the data folder.

    Args:
        file_path (str): The path to the file to read.
    
    Returns:
        str: The contents of the file.
    """
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()  # Extract text from each page

    return text
    

    

def get_tool() -> StructuredTool:
    return read_pdf_file

if __name__ == "__main__":
    print(read_pdf_file("core/jarvisDataSnack/Leksjon_ Intro til interaksjonsdesign.pdf"))