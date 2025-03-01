// TODO: add this port to .env later
var socket = new WebSocket("ws://localhost:3000/ws/your_session_id"); // ✅ FastAPI WebSockets

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
socket.onmessage = async function (event) {
  console.log(event.data);
  let message = JSON.parse(event.data);

  if (message.event === "chunk") {
      await handleChunk(message.data);
  } else if (message.event === "recording") {
      await handleRecording(message.data);
  } else if (message.event === "tokens") {
      await handleTokens(message.data);
  } else if (message.event === "start_message") {
      console.log("Start message event received.");
  } else if (message.event === "tool_call") {
      await handleToolCall(message.data);
  } else if (message.event === "tool_response") {
      await handleToolResponse(message.data);
  } else if (message.event === "chat_history") {
      await handleChatHistory(message.data);
  }
};


// Function to handle incoming "chunk" messages
async function handleChunk(chunk) {
  if (!state.activeAIMessage) {
      console.log("STARTED MESSAGE");
      uuid = generateUUID();
      await addStreamedMessage(uuid, "");
      ai_message = document.getElementById(uuid);
      state.activeAIMessage = ai_message;
  }
  await addStreamedMessage(uuid, chunk);
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

// Function to handle incoming "tool_call" messages
async function handleToolCall(tool_call) {
  console.log("Tool called: ", tool_call);
}

// Function to handle incoming "tool_response" messages
async function handleToolResponse(tool_response) {
  console.log("Response from tool: ", tool_response);
  if (tool_response.length > 0) {
      await addToolResponseToProcessContainer(tool_response);
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
