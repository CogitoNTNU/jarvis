import 'package:flutter/material.dart';
import '../../data/repositories/chat_repository.dart';

class ChatProvider extends ChangeNotifier {
  final ChatRepository chatRepository;
  List<Map<String, String>> messages = [];

  ChatProvider(this.chatRepository);

  Future<void> sendMessage(String userMessage) async {
    messages.add({"sender": "user", "text": userMessage});
    notifyListeners();

    String botReply = await chatRepository.sendMessage(userMessage);
    messages.add({"sender": "bot", "text": botReply});
    notifyListeners();
  }
}
