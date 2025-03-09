// TODO: add this port to .env later
var socket = new WebSocket("ws://localhost:3000/ws/placeholder_id"); // TODO: Replace placeholder_id with actual conversation ID

socket.onopen = function () {
  console.log("Connected to WebSocket server!");
  socket.send(JSON.stringify({ event: "get_chat_history" })); 
};

socket.onclose = function () {
  console.log("WebSocket closed.");
};

socket.onerror = function (error) {
  console.log("WebSocket error:", error);
};

// Function to handle incoming WebSocket messages
socket.onmessage = async function (ws_event) {
  let message = JSON.parse(ws_event.data);
  console.log(message.event);

  if (message.event === "ai_message") {
      await handleAiMessage(message.data);
  } else if (message.event === "recording") {
      await handleRecording(message.data);
  } else if (message.event === "tokens") {
      await handleTokens(message.data);
  } else if (message.event === "start_message") {
      console.log("Start message event received.");
  } else if (message.event === "tool_message") {
      await handleToolMessage(message.data);
  } else if (message.event === "chat_history") {
      await handleChatHistory(message.data);
  }
};


// Function to handle incoming "chunk" messages
async function handleAiMessage(message) {
  console.log(state.activeAIMessage)
  if (!state.activeAIMessage) {
      console.log("STARTED MESSAGE");
      uuid = generateUUID();
      await addStreamedMessage(uuid, "");
      ai_message = document.getElementById(uuid);
  }
  message = marked.parse(message)
  await addStreamedMessage(uuid, message);
}

// Function to handle incoming "recording" messages
async function handleRecording(recording) {
  if (!state.activeAIMessage) {
      console.log("RECEIVED MESSAGE");
      document.getElementById('voice_button').style.backgroundColor = ""; // Reset button color
      document.getElementById('voice_button').disabled = false; // Enable button
      uuid = generateUUID();
      await addStreamedRecording(uuid, "");
      ai_message = document.getElementById(uuid);
      state.activeAIMessage = ai_message;
  }
  await addStreamedRecording(uuid, recording);
}

// Function to handle incoming "tokens" messages
async function handleTokens(tokens) {
  state.totalTokensUsed += tokens;
  console.log("Total tokens so far:", state.totalTokensUsed);
  endStreamedAIMessage();
}

// Function to handle incoming "tool_response" messages
async function handleToolMessage(tool_message) {
  console.log("Response from tool: ", tool_message);
  if (tool_message.length > 0) {
      await addToolResponseToProcessContainer(tool_message);
  }
}

// Function to handle incoming "chat_history" messages
async function handleChatHistory(chatHistory) {
  console.log("Restoring chat history...");

  if (chatHistory.chat_history) {
      chatHistory.chat_history.forEach(entry => {
          addUserMessage(entry.human_message);
          addMessage(entry.ai_message);
      });
  }
}

console.log("socketEvents.js loaded...");