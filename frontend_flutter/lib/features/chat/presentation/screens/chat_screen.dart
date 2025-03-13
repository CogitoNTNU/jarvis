import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchPingMessage(); // Henter "ping" melding når chatten åpnes
  }

  Future<void> _fetchPingMessage() async {
    Uri url = Uri.http("http://llm-service:3000", '/ping_server');

    try {
      var response = await http.get(url);

      if (response.statusCode == 200) {
        final message = response.body;
        Provider.of<ChatProvider>(context, listen: false)
            .addMessage("bot", message);
      } else {
        print("Feil: ${response.statusCode} - ${response.body}");
      }
    } catch (e) {
      print("Feil ved forespørsel: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    final chatProvider = Provider.of<ChatProvider>(context);

    return Scaffold(
      backgroundColor: Color.fromARGB(255, 34, 34, 34),
      appBar: AppBar(
        toolbarHeight: 100,
        title: Padding(
          padding: EdgeInsets.only(top: 5.0, bottom: 20.0),
          child: ShaderMask(
            shaderCallback: (Rect bounds) {
              return LinearGradient(
                colors: [Colors.blue, Colors.lightBlueAccent, Colors.cyan],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ).createShader(bounds);
            },
            child: Text(
              "Jarvis Chat",
              style: TextStyle(
                fontSize: 80, // Gjør teksten større
                fontWeight: FontWeight.bold,
                color: Colors.white, // Påkrevd for ShaderMask
                shadows: [
                  Shadow(
                      blurRadius: 10.0,
                      color: Colors.blueAccent,
                      offset: Offset(2, 2)),
                  Shadow(
                      blurRadius: 20.0,
                      color: Colors.lightBlueAccent,
                      offset: Offset(-2, -2)),
                ],
              ),
            ),
          ),
        ),
        centerTitle: true,
        backgroundColor: Color.fromARGB(255, 34, 34, 34),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: chatProvider.messages.length,
              itemBuilder: (context, index) {
                final message = chatProvider.messages[index];
                final isUser = message['sender'] == 'user';

                return Padding(
                  padding: const EdgeInsets.only(left: 200.0),
                  // Adds spacing above the message
                  child: Align(
                    alignment: isUser
                        ? Alignment.centerLeft
                        : Alignment
                            .centerLeft, // ✅ Fixed center alignment for user
                    child: Container(
                      margin: EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                      padding: EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: isUser
                            ? Colors.white
                            : Colors.grey[800], // ✅ Better color choice
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Text(
                        message['text'] ?? "",
                        style: TextStyle(
                            color: Colors.black), // ✅ Ensures text is readable
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(
                      filled: true,
                      fillColor: Colors.grey[200],
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ),
                SizedBox(width: 10), // Litt luft mellom tekstfelt og knapp
                IconButton(
                  icon: Icon(Icons.send,
                      color: const Color.fromARGB(255, 255, 255, 255)),
                  onPressed: () {
                    if (_controller.text.trim().isNotEmpty) {
                      chatProvider.sendMessage(_controller.text.trim());
                      _controller.clear();
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose(); // ✅ Hindrer minnelekkasje
    super.dispose();
  }
}
