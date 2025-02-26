const silenceThreshold = 0.01;
const maxSilenceDuration = 3;
const maxRecordingDuration = 10000;
let silenceStartTime = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingTimeout;
let audioContext, analyser, source;
let conversationId = null;

const socket = io.connect(window.location.origin);

function startRecording() {
    document.getElementById('voice_button').style.backgroundColor = "#673636";
    document.getElementById('voice_button').disabled = true;
    conversationId = state.activeConversationId;
    commenceRecording(conversationId);
}

async function commenceRecording(conversation_id) {
    audioChunks = [];
    silenceStartTime = null;
    mediaRecorder = null;
    clearTimeout(recordingTimeout);

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();
    isRecording = true;


    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const combinedBlob = new Blob(audioChunks, { type: 'audio/webm' });

        const formData = new FormData();
        formData.append('audio', combinedBlob, 'recording.webm');

        try {
            const response = await fetch(`http://localhost:3001/upload_audio/${conversation_id}`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            console.log('Audio uploaded successfully');
        } catch (error) {
            console.error('Error uploading audio:', error);
        }
    };

    recordingTimeout = setTimeout(() => {
        if (isRecording) {
            console.log('Max recording time reached. Stopping...');
            mediaRecorder.stop();
        }
    }, maxRecordingDuration);

    detectSilence();
}

function detectSilence() {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const silenceCheckInterval = setInterval(() => {
        if (!isRecording || mediaRecorder.state === "inactive") {
            clearInterval(silenceCheckInterval);
            return;
        }

        analyser.getByteFrequencyData(dataArray);
        const averageVolume = dataArray.reduce((a, b) => a + b, 0) / bufferLength;

        const currentTime = performance.now();

        if (averageVolume < silenceThreshold * 255) {
            if (!silenceStartTime) {
                silenceStartTime = currentTime;
            }
        } else {
            silenceStartTime = null;
        }

        if (silenceStartTime && (currentTime - silenceStartTime) / 1000 >= maxSilenceDuration) {
            console.log('Silence detected. Stopping recording...');
            mediaRecorder.stop();
            clearInterval(silenceCheckInterval);
        }
    }, 500);
}
