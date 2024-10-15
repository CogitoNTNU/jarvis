console.log("Chat history module loaded...")
/*
Builds 
*/
let chatHistoryList = () => {
    let html = /*html*/ `
        <div id="chatHistoryList">
        <h3>Chat history</h3>
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

            </div>
        `
    }
    

    html += "</div>"
    return html
}