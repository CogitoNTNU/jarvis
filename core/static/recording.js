const silenceThreshold = 0.01;
const maxSilenceDuration = 3;
const maxRecordingDuration = 50000;
let silenceStartTime = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingTimeout;
let audioContext, analyser, source;
let conversationId = null;

let voice_button = document.getElementById('voice_button');

function startRecording() {
    if (voice_button == null) {
        voice_button = document.getElementById('voice_button');
    }
    if (isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        voice_button.style.backgroundColor = "";
        return;
    }
    voice_button.style.backgroundColor = "#673636";
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
        voice_button.style.backgroundColor = "";
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
            addUserMessage(marked.parse(data.message))
            console.log('Audio uploaded successfully');
            // Send the message via the open socket
            try{
                const payload = {prompt: data.message, conversation_id: String(state.activeConversationId)}
                let res = socket.send(JSON.stringify({ event: "user_prompt", data: payload }));
                // Stream to the current active AI chat box
            }catch(e){
                console.log("Something went wrong", e)
                chat_history.scrollTop = chat_history.scrollHeight;
            }
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
