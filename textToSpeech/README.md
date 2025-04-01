

```
curl -X POST \
  http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world. This is a test of the text-to-speech API. It should split this into sentences and generate audio for each one."}'
```