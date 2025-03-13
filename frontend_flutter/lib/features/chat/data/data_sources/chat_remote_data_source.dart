import 'package:frontend_flutter/core/network/api_client.dart';

class ChatRemoteDataSource {
  final ApiClient apiClient;

  ChatRemoteDataSource(this.apiClient);

  Future<String> sendMessage(String message) async {
    try{
      final response = await apiClient.post('/chat', {'message': message, 'session_id': "placeholder_id"});
      print("response was $response");
      return response['reply']; // Assuming backend returns {"reply": "response_text"}
    }catch(e){
      return "no response received. Error: $e";
    }
  }
}
