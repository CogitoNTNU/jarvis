startRecording = () => {
    document.getElementById('voice_button').style.backgroundColor = "#673636"; // Change button color to indicate recording
    document.getElementById('voice_button').enabled = false; // Disable button while recording
    const payload = {conversation_id: state.activeConversationId}
    let res = socket.emit('start_recording', payload)
    console.log("Recording started");
}