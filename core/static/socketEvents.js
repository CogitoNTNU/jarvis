// socket library is loaded beforehand

// TODO: add this port to .env later
var socket = io("ws://localhost:3000"); // websocket querying port 3001, where Flask is running.

socket.on('connect', () => {
    socket.emit('message', {data: 'I\'m connected!'});
});

let tokenCounter = 0
let msgCounter = 0

// prints tokens that are streamed to the console
socket.on("chunk", (token)=>{
    if (tokenCounter == 0 && token.length == 0){
        openStreamedAIMessage()
    }else if(token.length == 0){
        // Ending token received, close the message
        closeStreamedAIMessage()
        console.log("Tokens:", tokenCounter)

        state.totalTokensUsed += tokenCounter
        console.log("Total tokens so far:", state.totalTokensUsed)

        tokenCounter = 0
        msgCounter ++
    }else{
        console.log(token)
    }
    tokenCounter ++
})

let closeStreamedAIMessage = () => {
    console.log("Message end")
}

let openStreamedAIMessage = () => {
    console.log("Message start")
    // create an AI message in html, with its own ID (ai_message_0, ai_message_1 etc.)
    id = "ai_message_" + msgCounter
    // append to its innerText as the streams come through.
}

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