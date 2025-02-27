import '../data_sources/chat_remote_data_source.dart';

class ChatRepository {
  final ChatRemoteDataSource remoteDataSource;

  ChatRepository(this.remoteDataSource);

  Future<String> sendMessage(String message) async {
    return await remoteDataSource.sendMessage(message);
  }
}
