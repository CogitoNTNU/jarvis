import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';

class ChatScreen extends StatelessWidget {
  final TextEditingController _controller = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final chatProvider = Provider.of<ChatProvider>(context);

    return Scaffold(
      appBar: AppBar(title: Text("Jarvis Chat")),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: chatProvider.messages.length,
              itemBuilder: (context, index) {
                final message = chatProvider.messages[index];
                return Align(
                  alignment: message['sender'] == 'user'
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    margin: EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                    padding: EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: message['sender'] == 'user' ? Colors.blue : Colors.grey,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(message['text'] ?? ""),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(labelText: "Type your message"),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send),
                  onPressed: () {
                    chatProvider.sendMessage(_controller.text);
                    _controller.clear();
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
