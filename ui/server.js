const express = require('express')
const bodyParser = require('body-parser')
const app = express()
const fs = require('fs')

app.use(bodyParser.json())
app.use(express.static('public'))
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html')
})

// Links, constants
llm_url = 'http://llm-service:3001/send_message' // Can use "llm-service" and not internal ip thanks to docker

// TODO : Setup websockets to stream LLM output live to UI

app.listen(3000, () => {
    console.log('Server is running on http://localhost:3000')
})

messageLog = [] // History of the conversation - saved only on ui server