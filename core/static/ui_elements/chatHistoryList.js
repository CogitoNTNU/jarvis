console.log("Chat history module loaded...")
/*
Builds 
*/
let chatHistoryList = () => {
    let html = /*html*/ `
        <div id="chatHistoryList">
        <h3 class="russo-one-regular">Chat history</h3>
    `
    // Example chats. TODO: Do a GET request later on.
    let chats = [
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        },
        {
            name: "How to bake a cake",
            description: "Baking a cake: 1. Gather ingredients. 2. gather equipment. 3. Get..."
        }

    ]

    for (let i = 0; i < chats.length; i++){
        html += /*html*/ `
            <div class = "historicalChatThumbnail">
                <h3 class="chatThumbnailHeading">${chats[i].name}</h3>
                <p>${chats[i].description}</p>
            </div>
        `
    }
    

    html += "</div>"
    return html
}