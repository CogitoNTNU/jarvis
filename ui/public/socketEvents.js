// socket library is loaded beforehand

// TODO: add this port to .env later
var socket = io("localhost:3001"); // websocket querying port 3001, where Flask is running.
socket.on('connect', function() {
    socket.emit('message', {data: 'I\'m connected!'});
});

let emitEvent = async () => {
    let res = await socket.emit('message', {data: 'Hello from the site!'})
    console.log(res)
} 

console.log('socketEvents.js loaded...')