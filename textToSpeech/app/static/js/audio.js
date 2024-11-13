const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 10000,
    autoConnect: true
});

console.log('Attempting to connect to server...');

let audioContext;
let isProcessing = false;
let audioQueue = [];
let expectedSentenceId = 1;

socket.onAny((eventName, ...args) => {
    console.log(`Received event: ${eventName}`, args);
});

async function initAudioContext() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
}

async function processAudioChunk(audioData, sentenceId) {
    try {
        console.log(`Processing audio chunk for sentence ${sentenceId}`);
        const arrayBuffer = new Uint8Array(audioData).buffer;
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        
        // Add an event listener for when the audio finishes playing
        source.onended = () => {
            console.log(`Finished playing sentence ${sentenceId}`);
            expectedSentenceId++;
            isProcessing = false;
            processQueuedAudio(); // Process next chunk if available
        };
        
        source.start();
        isProcessing = true;
        
    } catch (error) {
        console.error('Error processing audio chunk:', error);
        isProcessing = false;
        processQueuedAudio(); // Try next chunk on error
    }
}

function processQueuedAudio() {
    if (isProcessing || audioQueue.length === 0) return;
    
    // Sort queue by sentence ID
    audioQueue.sort((a, b) => a.sentenceId - b.sentenceId);
    
    // Process next chunk if it matches expected ID
    const nextChunk = audioQueue[0];
    if (nextChunk.sentenceId === expectedSentenceId) {
        audioQueue.shift(); // Remove from queue
        processAudioChunk(nextChunk.audioData, nextChunk.sentenceId);
    }
}

// Socket.IO event handler
socket.on('audio_stream', async (data) => {
    console.log('Received audio_stream event:', {
        sentenceId: data.sentence_id,
        dataLength: data.audio_data.length
    });
    
    if (!audioContext) {
        console.log('Initializing audio context');
        await initAudioContext();
    }
    
    const audioData = new Uint8Array(data.audio_data);
    const sentenceId = data.sentence_id;
    
    // Reset state if this is the start of a new generation
    if (sentenceId === 1) {
        console.log('New text generation - resetting client state');
        expectedSentenceId = 1;
        audioQueue = [];
        isProcessing = false;
    }
    
    console.log(`Queueing audio chunk ${sentenceId}`);
    
    // Queue the audio chunk
    audioQueue.push({
        audioData: audioData,
        sentenceId: sentenceId,
        timestamp: Date.now()
    });
    
    console.log(`Current queue length: ${audioQueue.length}`);
    // Try to process queued audio
    processQueuedAudio();
});

// Initialize audio context on user interaction
document.addEventListener('click', async () => {
    if (!audioContext) {
        await initAudioContext();
    }
    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }
});

socket.on('test', (data) => {
    console.log('Received test message:', data);
    status.textContent = "Status: Received test message";
});

socket.on('connecting', () => {
    console.log('Attempting to connect...');
    status.textContent = "Status: Attempting to connect...";
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    console.log('Transport type:', socket.io.engine.transport.name);
    status.textContent = `Status: Connection error - ${error.message}`;
});

socket.on('connect_timeout', () => {
    console.error('Connection timeout');
    status.textContent = "Status: Connection timeout";
});

socket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Reconnection attempt ${attemptNumber}`);
    status.textContent = `Status: Reconnection attempt ${attemptNumber}`;
});

socket.on('connect', () => {
    console.log('Connected to server with ID:', socket.id);
    console.log('Transport type:', socket.io.engine.transport.name);
    status.textContent = "Status: Connected to server. Click anywhere to enable audio.";
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    status.textContent = "Status: Disconnected from server";
}); 