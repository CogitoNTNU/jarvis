import os
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool


@tool 
def read_file(file_path: str):
    """
    Use this tool to read the contents of a file. 
    The file path should be relative to the data folder. 

    Args:
        file_path (str): The path to the file to read. 

    Returns:
        str: The contents of the file. 
    """

    with open(file_path, 'r') as file:
        return file.read()

def get_tool() -> StructuredTool:
    return read_file