README for speech module

pip install -r requirements.txt

include a .env file with:
    OPENAI_API_KEY = myapikey

The speech to text script can convert audio files to text, and use the audiorecorder to record input from the user.

### Run speech to text with record
```python speech_to_text.py```
This will record audio and print the retruned text until it is stopped, or silence is detected for more than 5 seconds.

### Run speech to text on audiofile
```python speech_to_text.py <filepath>``` 
This will convert the audio file on the given path.


### Process audio file
```python audioProcessor.py <inputpath> <outputpath>```

### Boost audio levels
```python audioProcessor.py boost <filepath> <boostfactor>```

