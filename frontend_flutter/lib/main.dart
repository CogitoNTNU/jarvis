import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/network/api_client.dart';
import 'features/chat/data/data_sources/chat_remote_data_source.dart';
import 'features/chat/data/repositories/chat_repository.dart';
import 'features/chat/presentation/providers/chat_provider.dart';
import 'features/chat/presentation/screens/chat_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>(create: (_) => ApiClient()), // Provide API Client

        Provider<ChatRemoteDataSource>(
            create: (context) =>
                ChatRemoteDataSource(context.read<ApiClient>())),

        Provider<ChatRepository>(
            create: (context) =>
                ChatRepository(context.read<ChatRemoteDataSource>())),

        ChangeNotifierProvider(
            create: (context) => ChatProvider(
                context.read<ChatRepository>())), // Fix: Pass ChatRepository
      ],
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
            useMaterial3: true,
            textTheme: TextTheme(
                bodyLarge: TextStyle(
              fontSize: 32,
            ))),
        initialRoute: '/chat',
        routes: {
          '/chat': (context) => ChatScreen(),
        },
      ),
    );
  }
}
