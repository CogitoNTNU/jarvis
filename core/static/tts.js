// TODO:  Remove random debugging stuff
// Check if socket already exists, if not create it

let ttsSocket = (() => {
    const config = {
        websocketServer: 'http://localhost:5000'
    };

    return io(config.websocketServer, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 10000,
        autoConnect: true,
    });
})();

console.log('Attempting to connect to server...');

let audioContext2;
let isProcessing = false;
let audioQueue = [];
let expectedSentenceId = 1;

// Update all socket references to ttsSocket
ttsSocket.onAny((eventName, ...args) => {
    console.log(`Received event: ${eventName}`, args);
});

ttsSocket.on('connecting', () => {
    console.log('Attempting to connect...');
});

ttsSocket.on('connect', () => {
    console.log('Connected to remote WebSocket server:', ttsSocket.io.uri);
    console.log('Connected to server with ID:', ttsSocket.id);
    console.log('Transport type:', ttsSocket.io.engine.transport.name);
});

ttsSocket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    console.log("DISABLING TTS FOR NOW - NO NARAKEET API KEY OR SOMETHING ELSE IS BROKEN IN TE BACKEND")
    ttsSocket = {}
    console.log('Failed connecting to:', ttsSocket.io.uri);
    console.log('Transport type:', ttsSocket.io.engine.transport.name);
});

ttsSocket.on('connect_timeout', () => {
    console.error('Connection timeout');
});

ttsSocket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Reconnection attempt ${attemptNumber}`);
});

ttsSocket.on('disconnect', () => {
    console.log('Disconnected from server');
});

async function initAudioContext() {
    audioContext2 = new (window.AudioContext || window.webkitAudioContext)();
}

async function processAudioChunk(audioData, sentenceId) {
    try {
        console.log(`Processing audio chunk for sentence ${sentenceId}`);
        const arrayBuffer = new Uint8Array(audioData).buffer;
        const audioBuffer = await audioContext2.decodeAudioData(arrayBuffer);
        
        const source = audioContext2.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext2.destination);
        
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
ttsSocket.on('audio_stream', async (data) => {
    console.log('Received audio_stream event:', {
        sentenceId: data.sentence_id,
        dataLength: data.audio_data.length
    });
    
    if (!audioContext2) {
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
    if (!audioContext2) {
        await initAudioContext();
    }
    if (audioContext2.state === 'suspended') {
        await audioContext2.resume();
    }
});

ttsSocket.on('test', (data) => {
    console.log('Received test message:', data);
});

ttsSocket.on('connect', () => {
    console.log('Connected to remote WebSocket server:', ttsSocket.io.uri);
    console.log('Connected to server with ID:', ttsSocket.id);
    console.log('Transport type:', ttsSocket.io.engine.transport.name);
});

ttsSocket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    console.log('Failed connecting to:', ttsSocket.io.uri);
    console.log('Transport type:', ttsSocket.io.engine.transport.name);
});

ttsSocket.on('connect_timeout', () => {
    console.error('Connection timeout');
});

ttsSocket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Reconnection attempt ${attemptNumber}`);
});

ttsSocket.on('disconnect', () => {
    console.log('Disconnected from server');
});

ttsSocket.on('connect', () => {
    console.log('Connected to remote WebSocket server:', ttsSocket.io.uri);
    console.log('Transport type:', ttsSocket.io.engine.transport.name);
});

ttsSocket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    console.log('Failed connecting to:', ttsSocket.io.uri);
}); 