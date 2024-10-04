import os
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool

@tool
def find_files():
    """
    Use this tool to find the names and locations of all files in the data folder. 
    These files can be read by using other tools. When a user asks for any data, always 
    check if a relevant file exists in the data folder. If it does, use the read_file tool 
    to read the contents of the file.

    Returns:
        list[str]: A list of file names and locations in the data folder.
    """

    file_list = []
    start = 'jarvisDataSnack/'
    for root, dirs, files in os.walk(start):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), '.')
            file_list.append(relative_path)
    
    return file_list

def get_tool() -> StructuredTool:
    return find_files

