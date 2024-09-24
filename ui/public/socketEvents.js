// socket library is loaded beforehand

// TODO: add this port to .env later
var socket = io("ws://localhost:3001"); // websocket querying port 3001, where Flask is running.

socket.on('connect', () => {
    socket.emit('message', {data: 'I\'m connected!'});
});

// prints tokens that are streamed to the console
socket.on("chunk", (token)=>{
    console.log(token)
    console.log('GOT A CHUNK')
})

let emitEvent = async () => {
    let res = await socket.emit('message', {data: 'Hello from the site!'})
    console.log(res)
}

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