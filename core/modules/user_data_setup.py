import os

def check_folders():
    main_folder = "user_data/"
    pathsToCheck = ["chats", "chats_metadata"]
    for directory in pathsToCheck:
        path = main_folder + directory # creates path user_data/chats for example. Everything should be under user_data as its gitignored.
        check_and_create_folder(path) # Does a relative folder check, and builds the directory if it doesn't exist

def check_and_create_folder(path):
    dirname = os.path.dirname(os.path.dirname(__file__)) # Creates folder in core named user_data
    relativedir = os.path.join(dirname, path)
    if not os.path.exists(relativedir):
        try:
            print("Created user_data director under core folder. This is first-time setup.")
            os.makedirs(path)
        except Exception as e:
            print(e)