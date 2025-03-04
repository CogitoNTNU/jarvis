// When user sends a message (pressing send button) this funciton runs
sendMessage = () => {
    let userInput = ""
    try{
        let chat_text_field = document.getElementById('chat_input_text')
        userInput = chat_text_field.value
        addUserMessage(marked.parse(userInput))
        chat_text_field.value = ""
        chat_history = document.getElementById("chat_history")
        chat_history.scrollTop = chat_history.scrollHeight;
    } catch(e){
        console.log(e)
    }

    // Send the message via the open socket
    try{
        const payload = {prompt: userInput, conversation_id: String(state.activeConversationId)}
        let res = socket.send(JSON.stringify({ event: "user_prompt", data: payload }));
        // Stream to the current active AI chat box
    }catch(e){
        console.log("Something went wrong", e)
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}

addRecordedMessage = (message) => {
    let chat_history = document.getElementById("chat_history")
    if (message != "") {
    addUserMessage(marked.parse(message))
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}


addStreamedChunk = (messagePart) => {
    if(state.activeAIMessage){
        state.activeAIMessage.innerHTML += messagePart; // Append to innertext of the message
        let chat_history = document.getElementById("chat_history")
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}

endStreamedAIMessage = () => {
    if (state.activeAIMessage) {
        console.log("Message end")
        let output = state.activeAIMessage.innerHTML
        output = marked.parse(output)
        state.activeAIMessage.innerHTML = output
        state.activeAIMessage = null // Gets deleted from the state.
    } else {
        console.log("No active AI message to end.")
    }

}

// Generates unique id on socket.on("start_message")
let generateUUID = () => {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
        (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
    );
}
