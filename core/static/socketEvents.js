// socket library is loaded beforehand

// TODO: add this port to .env later
var socket = io("ws://localhost:3000"); // websocket querying port 3001, where Flask is running.

socket.on('connect', () => {
    socket.emit('message', {data: 'I\'m connected!'});
});

let tokenCounter = 0
let msgCounter = 0
let uuid = 0

// prints tokens that are streamed to the console
socket.on("chunk", (chunk)=>{
    if (chunk.length == 0){ // Ending token received, close the message
        endStreamedAIMessage()
        console.log("Tokens:", tokenCounter)

        state.totalTokensUsed += tokenCounter
        console.log("Total tokens so far:", state.totalTokensUsed)

        tokenCounter = 0
        msgCounter ++
    }else{
        console.log(chunk);
        addStreamedChunk(chunk);
    }
    tokenCounter ++;
})

socket.on("tokens", (tokens) => {
    state.totalTokensUsed += tokens
    console.log("Total tokens so far:", state.totalTokensUsed)
})

socket.on("start_message", () => {
    uuid = generateUUID();
    console.log(uuid);
    startStreamedAIMessage(uuid)
})

// Remember to parse the streamed response

/*
        let shouldParse = document.getElementById("checkbox").checked
        if(shouldParse){
            addMessage(marked.parse(json.aiResponse.message))
        }else{
            addMessage((json.aiResponse.message))
        }
        let chat_history = document.getElementById("chat_history")
        chat_history.scrollTop = chat_history.scrollHeight;
*/

console.log('socketEvents.js loaded...')