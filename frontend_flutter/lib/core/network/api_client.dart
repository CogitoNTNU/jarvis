import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl = "http://localhost:3000";

     Future<Map<String, dynamic>> post(String endpoint, Map<String, dynamic> data) async {
        try{
        String encodedData = jsonEncode(data);
        final response = await http.post(
          Uri.parse('$baseUrl$endpoint'),
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
          },
          body: encodedData,
        );
        print(response.statusCode);
        Map<String, dynamic> decodedJson = jsonDecode(response.body);
        print(decodedJson);
        print(decodedJson.runtimeType);

        if (response.statusCode == 200) {
          return jsonDecode(response.body);
        } else {
          throw Exception("Failed to connect: ${response.body}");
        }
        }catch(e){
          return {"error:": e};
        }
    } 

}
