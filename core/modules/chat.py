import os
import json

def read_chat(id): 
    '''
    Uses chat_id to get the entire chat JSON file
    '''
    dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
    filepath = os.path.join(dirname, f'user_data/chats/{id}.json')
    # Open and read the JSON file
    with open(filepath, 'r') as file:
        data = json.load(file)

    # Print the data
    print(data)