window.addEventListener('keyup', (event) => {
    if(event.key == "Enter" && !event.shiftKey){
        sendMessage()
    }
})