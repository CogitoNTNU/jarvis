const silenceThreshold = 10; // RMS threshold to detect silence
const maxSilenceDuration = 3; // seconds
let silenceStartTime = null;
let mediaRecorder, audioChunks = [];
let isRecording = false;

// Connect to the WebSocket server
const socket = io.connect(window.location.origin);

// Listen for "start_recording" event
socket.on('start_recording', () => {
    document.getElementById('status').innerText = "Recording started by server...";
    startRecording();
});

// Start recording audio
async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Create MediaRecorder instance
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();

    isRecording = true;
    document.getElementById('status').innerText = "Recording in progress...";

    // Collect audio data chunks
    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };

    // When the recording stops, we process and upload the audio
    mediaRecorder.onstop = async () => {
        // Combine audio chunks into a single Blob
        const combinedBlob = new Blob(audioChunks, { type: 'audio/webm' });

        // Send the WebM file to the server (no conversion needed)
        const formData = new FormData();
        formData.append('audio', combinedBlob, 'recording.webm');

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

    // Detect silence during the recording
    detectSilence();
}

// Detect silence based on time and silenceThreshold
function detectSilence() {
    const silenceCheckInterval = setInterval(() => {
        if (mediaRecorder.state === "inactive" || !isRecording) {
            clearInterval(silenceCheckInterval);
            return;
        }

        // Here, we're checking if the audio chunks' duration is long enough to consider it "silence".
        const currentTime = performance.now();

        if (audioChunks.length === 0) {
            // If no data has been recorded yet, we consider it silent
            if (!silenceStartTime) {
                silenceStartTime = currentTime; // Start the silence timer
            }
        } else {
            // Sound is detected, reset the silence timer
            silenceStartTime = null;
        }

        // Check if silence duration exceeds the maximum silence duration
        if (silenceStartTime && (currentTime - silenceStartTime) / 1000 >= maxSilenceDuration) {
            document.getElementById('status').innerText = "Silence detected. Stopping recording...";
            mediaRecorder.stop(); // Stop recording when silence is detected
            clearInterval(silenceCheckInterval); // Stop checking for silence
        }
    }, 1000);

    
}
