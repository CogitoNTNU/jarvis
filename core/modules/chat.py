import os
import json

def read_chat(id: str) -> dict:
    '''
    Uses chat_id to get the chat JSON file and returns a python dict object.
    '''
    try:
        dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
        filepath = os.path.join(dirname, f'user_data/chats/{id}.txt')
        # Open and read the chat txt file
        with open(filepath, 'r') as file:
            raw_text = file.read()
            chat = json.loads("[" + raw_text + "]") # creates a dict by wrapping all messages as an array, making it valid json. Then loading it using json.load.
        return chat
    except Exception as e:
        return e

def append_message_to_chat(message: dict, id: str):
    try:
        dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
        filepath = os.path.join(dirname, f'user_data/chats/{id}.txt')
        # Convert json to text and prepare for appending
        message_txt = json.dump(message)
        message_txt = f"\n,{message_txt}"
        # Open the chat file
        with open(filepath, 'a') as file:
            file.write(message_txt)
    except Exception as e:
        return e

# def upsert_chat(chat_object: dict, id: str):
#     '''
#         Upserts a chat dictionary object, saving it as json file in the user_data folder.
#         Upserting means to update or create if the file doesn't exist yet. Overwriting previous data.
#     '''
#     try:
#         dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
#         filepath = os.path.join(dirname, f'user_data/chats/{id}.txt')
#         # Open and write the JSON file
#         with open(filepath, 'w') as file:
#             file.write(json.dump(chat_object))
#         return True # Returns true if successfull
#     except Exception as e:
#         return e

# json.dumps() - From python to json
# json.load() - From json to python