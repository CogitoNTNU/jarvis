startRecording = () => {
    console.log("Recording started");
    const payload = {conversation_id: state.activeConversationId}
    let res = socket.emit('start_recording', payload)
}