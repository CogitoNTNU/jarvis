/*

Main js file for loading the dynamic UI elements.
    
*/

// Runs on inital startup, after window (html) has finished loading
 init = () => {
    document.getElementById('send_button').addEventListener('click', sendMessage)
    document.getElementById('clear_log').addEventListener('click', clear_log)
}
window.onload = init;

// global state of the UI
state = {
    activeConversationId: 0, // The active conversation ID, so the UI knows what conversation to display and load.
    userId: 0, // The user ID using the interface. probably not going to be used for a while.
    totalTokensUsed: 0,  // Track of total tokens and $$$ used
    aiMessageId: 0 // The message id. Set when a response is received from the AI in chat.js
}

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

// For seeing formatted HTML in javascript files, this extension for VSCode is recommended:
// https://marketplace.visualstudio.com/items?itemName=pushqrdx.inline-html

async function addMessage(message, uuid) {
let html = /*html*/`
    <li class = "chat_element">
        <img class="profile_picture" src="./static/trainer.png">
        <div class="chat_message_container">
            <div id=${uuid} class="chat_message"> ${message} </div>
    </li>`;
    document.getElementById('chat_history').innerHTML += html;
}

async function addStreamedMessage(uuid, messagePart) {
    let element = document.getElementById(uuid);

    if (element == null) {
        await addMessage(messagePart, uuid);
        element = document.getElementById(uuid);
    } else {
        // Concat ChatPart on message with uuid
        element.innerHTML += messagePart;
    }
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

initialLoadMessages = () => {
    const chat_box = document.getElementById('chat_history')
    allChats = []
    chat_box.value = messageLog.join('\n')
}