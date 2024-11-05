const silenceThreshold = 10; // RMS threshold to detect silence
const maxSilenceDuration = 1; // seconds
let silenceStartTime = null;
let mediaRecorder, audioBlob;

// Connect to the WebSocket server
const socket = io.connect(window.location.origin);

// Listen for "start_recording" event
socket.on('start_recording', () => {
    document.getElementById('status').innerText = "Recording started by server...";
    startRecording();
});

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();

    // Initialize the audioBlob to store recorded data
    audioBlob = new Blob([], { type: 'audio/wav' });

    // Append data when available
    mediaRecorder.ondataavailable = event => {
        audioBlob = new Blob([audioBlob, event.data], { type: 'audio/wav' });
    };

    // Stop recording when silence is detected
    mediaRecorder.onstop = async () => {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        try {
            const response = await fetch('/upload_audio', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            console.log(data);
            document.getElementById('status').innerText = `Audio uploaded. Server response: ${data.message}`;
        } catch (error) {
            console.error('Error uploading audio:', error);
            document.getElementById('status').innerText = 'Error uploading audio';
        }
    };

    // Check for silence
    detectSilence();
}

function detectSilence() {
    const silenceCheckInterval = setInterval(() => {
        if (mediaRecorder.state === "inactive") {
            clearInterval(silenceCheckInterval);
            return;
        }

        // Check for sound levels
        const currentTime = performance.now();
        
        if (audioBlob.size === 0) {
            // If no data has been recorded yet, we consider it silent
            if (!silenceStartTime) {
                silenceStartTime = currentTime; // Start the silence timer
            }
        } else {
            // Sound is detected
            silenceStartTime = null; // Reset the silence timer
        }

        // Check if silence duration exceeds the maximum silence duration
        if (silenceStartTime && (currentTime - silenceStartTime) / 1000 >= maxSilenceDuration) {
            document.getElementById('status').innerText = "Silence detected. Stopping recording...";
            mediaRecorder.stop();
            clearInterval(silenceCheckInterval); // Stop checking for silence
        }
    }, 1000);
}
