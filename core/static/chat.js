// When user sends a message (pressing send button) this funciton runs
sendMessage = async () => {
    let chat_text_field = document.getElementById('chat_input_text')
    const user_input = chat_text_field.value
    addUserMessage(marked.parse(user_input))
    chat_text_field.value = ""
    chat_history = document.getElementById("chat_history")
    chat_history.scrollTop = chat_history.scrollHeight;

    // Send a message to node, which forwards to llm-service to get the response from the chatbot
    try{
        let res = await socket.emit('user_prompt', {prompt: user_input, conversation_id: active_conversation_id})
        console.log(res)
        // Stream to the current active AI chat box
    }catch(e){
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}