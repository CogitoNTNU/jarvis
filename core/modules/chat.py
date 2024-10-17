import os
import json

def read_chat(id: str) -> dict:
    '''
    Uses chat_id to get the chat JSON file and returns a python dict object.
    '''
    dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
    filepath = os.path.join(dirname, f'user_data/chats/{id}.json')
    # Open and read the JSON file
    with open(filepath, 'r') as file:
        data = json.load(file)
    return data

def upsert_chat(chat_object: dict):
    '''
        Upserts a chat dictionary object, saving it as json file in the user_data folder.
        Upserting means to update or create if the file doesn't exist yet. Overwriting previous data.
    '''
    try:
        print("hey")
    except Exception as e:
        return e


# json.dumps() - From python to json
# json.load() - From json to python