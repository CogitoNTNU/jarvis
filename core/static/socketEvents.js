// socket library is loaded beforehand

// TODO: add this port to .env later
var socket = io("ws://localhost:3000"); // websocket querying port 3001, where Flask is running.

socket.on('connect', () => {
    socket.emit('message', {data: 'I\'m connected!'});
});

let tokenCounter = 0
let uuid = 0

// prints chunks that are streamed to the console and adds them to the chat
socket.on("chunk", async (chunk)=>{
    console.log(chunk);
    await addStreamedMessage(uuid, chunk);
})

socket.on("tokens", async (tokens) => {
    state.totalTokensUsed += tokens
    console.log("Total tokens so far:", state.totalTokensUsed)
    endStreamedAIMessage()
})

socket.on("start_message", async () => {
    uuid = generateUUID();
    console.log(uuid);
    await addStreamedMessage(uuid, "");
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