// Runs on inital startup, after window (html) has finished loading
init = () => {
    document.getElementById('send_button').addEventListener('click', sendMessage)
    document.getElementById('clear_log').addEventListener('click', clear_log)
}
window.onload = init;

clear_log = async () => {
    try{
        res = await fetch('/clear_chat_history')
        result = await res.json()
        console.log(result)
        chat_history.innerHTML = ""
        alert("Chatlog cleared successfully!")
    }catch(e){
        console.log("It borked")
    }
}

// Placeholder
conversation_id = 0

// Changes the loading icon
let loading = false
let setLoading = (newLoadingVal) => {
    if(newLoadingVal){
        document.getElementById("chat_history").innerHTML += /* html */`
    <div id="spinner" class="dot-spinner">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
    </div>`
    }else{
        try{
            document.getElementById("spinner").remove()
        }catch(e){

        }
    }

    loading = newLoadingVal
}

// When user sends a message (pressing send button) this funciton runs
sendMessage = async () => {
    let chat_text_field = document.getElementById('chat_input_text')
    const user_input = chat_text_field.value
    addUserMessage(marked.parse(user_input))
    chat_text_field.value = ""
    setLoading(true)
    chat_history = document.getElementById("chat_history")
    chat_history.scrollTop = chat_history.scrollHeight;

    // Send a message to node, which forwards to llm-service to get the response from the chatbot
    try{
        res = await fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: user_input, conversation_id, source: 'user',})
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

window.addEventListener('keyup', (event) => {
    if(event.key == "Enter" && !event.shiftKey){
        sendMessage()
    }
})

// For seeing formatted HTML in javascript files, this extension for VSCode is recommended:
// https://marketplace.visualstudio.com/items?itemName=pushqrdx.inline-html

addMessage = (message) => {
    let html = /*html*/`
    <li class = "chat_element">
        <img class="profile_picture" src="./trainer.png">
        <div class="chat_message_container">
            <div class="chat_message">${message}</div>
    </li>`
    document.getElementById('chat_history').innerHTML += html;
}

addUserMessage = (message) => {
    let html = /*html*/`
    <li class = "chat_element">
        <img class="profile_picture" src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Ftoppng.com%2Fpublic%2Fuploads%2Fpreview%2Fuser-account-management-logo-user-icon-11562867145a56rus2zwu.png&f=1&nofb=1&ipt=5314f437c2b8d23762941ef06df17a94034191b5759f8871931e3fb0def23aed&ipo=images">
        <div class="chat_message_container">
            <div class="chat_message">${message}</div>
    </li>`
    document.getElementById('chat_history').innerHTML += html;
}

buildRecievingMessage = async () => {

}

initialLoadMessages = () => {
    const chat_box = document.getElementById('chat_history')
    allChats = []
    chat_box.value = messageLog.join('\n')
}

let workouts = [
    {
        name: "backday",
        volume: 3000,
        date: Date.now(),
        exercises: [
            {name: "lat pulldowns", reps: 3, weight: 90},
            {name: "lat pulldowns", reps: 3, weight: 90},
            {name: "lat pulldowns", reps: 3, weight: 90},
            {name: "Dumbbell row", reps: 10, weight: 27.5},
            {name: "Dumbbell row", reps: 10, weight: 27.5},
            {name: "Dumbbell row", reps: 10, weight: 27.5},
            {exerciseId: "Dumbbell row", reps: 10, weight: 27.5},
        ]
    }
]