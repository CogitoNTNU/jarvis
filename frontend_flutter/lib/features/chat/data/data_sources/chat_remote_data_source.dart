import 'package:frontend_flutter/core/network/api_client.dart';

class ChatRemoteDataSource {
  final ApiClient apiClient;

  ChatRemoteDataSource(this.apiClient);

  Future<String> sendMessage(String message) async {
    final response = await apiClient.post('/chat', {'message': message});
    return response['reply']; // Assuming backend returns {"reply": "response_text"}
  }
}
