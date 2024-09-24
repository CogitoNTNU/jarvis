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

    // Send a message to node, which forwards to llm-service to get the response from the chatbot
    try{
        let res = await socket.emit('user_prompt', {prompt: userInput, conversation_id: state.activeConversationId})
        // Stream to the current active AI chat box
    }catch(e){
        console.log("Something went wrong", e)
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}