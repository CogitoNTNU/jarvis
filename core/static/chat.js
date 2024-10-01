// When user sends a message (pressing send button) this funciton runs
sendMessage = async () => {
    let userInput = ""
    try{
        let chat_text_field = document.getElementById('chat_input_text')
        userInput = chat_text_field.value
        addUserMessage(marked.parse(userInput))
        chat_text_field.value = ""
        chat_history = document.getElementById("chat_history")
        chat_history.scrollTop = chat_history.scrollHeight;
    }catch(e){
        console.log(e)
    }

    // Send the message via the open socket
    try{
        let res = await socket.emit('user_prompt', {prompt: userInput, conversation_id: state.activeConversationId})
        // Stream to the current active AI chat box
    }catch(e){
        console.log("Something went wrong", e)
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}

addStreamedChunk = (messagePart) => {
    if(state.activeAIMessage){
        state.activeAIMessage.innerText += messagePart; // Append to innertext of the message
    }
}

let endStreamedAIMessage = () => {
    console.log("Message end")
    state.activeAIMessage = null // Gets deleted from the state.
}

let startStreamedAIMessage = (uuid) => {
    console.log("Message start")
    addMessage(uuid); // Create an AI message when it begins streaming.
    let ai_message = document.getElementById(uuid)
    state.activeAIMessage = ai_message // Active element gets added to the state.
}

// Generates unique id on socket.on("start_message")
let generateUUID = () => {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
        (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
    );
}
