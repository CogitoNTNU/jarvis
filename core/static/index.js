// Runs on inital startup, after window (html) has finished loading
init = () => {
    document.getElementById('send_button').addEventListener('click', sendMessage)
    document.getElementById('clear_log').addEventListener('click', clear_log)
}
window.onload = init;

// global state of the UI
state = {
    activeConversationId: 0,
    userId: 0,
    totalTokensUsed: 0
}

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

initialLoadMessages = () => {
    const chat_box = document.getElementById('chat_history')
    allChats = []
    chat_box.value = messageLog.join('\n')
}