// Generate a unique session ID and store it in localStorage
function getSessionId() {
    let storedId = localStorage.getItem('jarvis_session_id');
    if (!storedId) {
        storedId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('jarvis_session_id', storedId);
    }
    return storedId;
}

let session_id = getSessionId();
let socket;
let reconnectInterval = 2000; // Start with 2 seconds
let maxReconnectInterval = 30000; // Max 30 seconds between retries
let reconnectAttempts = 0;
let maxReconnectAttempts = 10;

function connectWebSocket() {
    // Always get the latest session ID when connecting
    session_id = getSessionId();
    socket = new WebSocket("ws://localhost:3000/ws/" + session_id);
    
    socket.onopen = function() {
        console.log("Connected to WebSocket server!");
        reconnectInterval = 2000; // Reset reconnect interval
        reconnectAttempts = 0;
        socket.send(JSON.stringify({ event: "get_chat_history" }));
    };
    
    socket.onclose = function(event) {
        console.log("WebSocket closed. Attempting to reconnect...", event.code, event.reason);
        
        // Reset connection if server explicitly closed it with certain codes
        if (event.code === 1001 || event.code === 1006) {
            console.log("Server closed connection. Generating new session ID...");
            localStorage.removeItem('jarvis_session_id'); // Force new session ID
            session_id = getSessionId(); // Get fresh session ID
        }
        
        // Only try to reconnect if we haven't exceeded max attempts
        if (reconnectAttempts < maxReconnectAttempts) {
            setTimeout(connectWebSocket, reconnectInterval);
            reconnectInterval = Math.min(reconnectInterval * 1.5, maxReconnectInterval);
            reconnectAttempts++;
        } else {
            console.error("Max reconnection attempts reached");
            // Reset after a longer timeout so we can try again
            setTimeout(() => {
                reconnectAttempts = 0;
                reconnectInterval = 2000;
                localStorage.removeItem('jarvis_session_id'); // Force new session ID for fresh start
                session_id = getSessionId();
                connectWebSocket();
            }, 60000);
        }
    };
    
    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
    };
    
    socket.onmessage = async function(ws_event) {
        // Your existing message handling code
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
}

// Initialize connection
connectWebSocket();

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

// Add this function to socketEvents.js
async function checkConnectionHealth() {
    try {
        const response = await fetch(`http://localhost:3000/ws/health/${session_id}`);
        const data = await response.json();
        
        if (data.status === "disconnected" && socket.readyState === WebSocket.OPEN) {
            console.log("Server reports disconnected but client thinks connected. Reconnecting...");
            socket.close();
        }
    } catch (error) {
        console.error("Health check failed:", error);
    }
}

// Run health check periodically
setInterval(checkConnectionHealth, 30000); // Every 30 seconds

console.log("socketEvents.js loaded...");