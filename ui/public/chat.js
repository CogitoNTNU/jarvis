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
        let res = await socket.emit('user_prompt', {prompt: user_input, conversation_id: active_conversation_id, source: 'user'})
        console.log(res)
    }catch(e){
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}

/*
sendMessage = async () => {
    let chat_text_field = document.getElementById('chat_input_text')
    const user_input = chat_text_field.value
    addUserMessage(marked.parse(user_input))
    chat_text_field.value = ""
    setLoading(true)
    chat_history = document.getElementById("chat_history")
    chat_history.scrollTop = chat_history.scrollHeight;

    console.log(user_input)

    // Send a message to node, which forwards to llm-service to get the response from the chatbot
    try{
        let payload = {}
        try{
            payload = JSON.stringify({ 
                message: user_input, // gathered from the html page
                active_conversation_id, // global variable from index.js
                source: 'user',})
        }catch(e){
            console.log(e)
        }

        res = await fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: payload
        })
        
        let json = await res.json()
        let shouldParse = document.getElementById("checkbox").checked
        
        if(shouldParse){
            addMessage(marked.parse(json.aiResponse.message))
        }else{
            addMessage((json.aiResponse.message))
        }
        let chat_history = document.getElementById("chat_history")
        chat_history.scrollTop = chat_history.scrollHeight;
        setLoading(false)

    }catch(e){
        setLoading(false)
        chat_history.scrollTop = chat_history.scrollHeight;
    }
}
*/