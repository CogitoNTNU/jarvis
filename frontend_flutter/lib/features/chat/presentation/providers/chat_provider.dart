import 'package:flutter/material.dart';
import '../../data/repositories/chat_repository.dart';

class ChatProvider extends ChangeNotifier {
  final ChatRepository chatRepository;

  ChatProvider(this.chatRepository);

  List<Map<String, String>> messages = [];

  void addMessage(String sender, String text) {
    messages.add({"sender": sender, "text": text});
    notifyListeners();
  }

  Future<void> sendMessage(String userMessage) async {
    addMessage("user", userMessage);

    String botReply = await chatRepository.sendMessage(userMessage);
    addMessage("bot", botReply);
  }
}
