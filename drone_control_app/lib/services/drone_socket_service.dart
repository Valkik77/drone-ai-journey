import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

enum ConnectionStatus { disconnected, connecting, connected, error }

class Telemetry {
  final double x;
  final double y;
  final double z;

  const Telemetry({this.x = 0, this.y = 0, this.z = 0});

  factory Telemetry.fromJson(Map<String, dynamic> json) {
    return Telemetry(
      x: (json['x'] as num?)?.toDouble() ?? 0,
      y: (json['y'] as num?)?.toDouble() ?? 0,
      z: (json['z'] as num?)?.toDouble() ?? 0,
    );
  }
}

class DroneSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  final ValueNotifier<ConnectionStatus> status =
      ValueNotifier(ConnectionStatus.disconnected);
  final ValueNotifier<Telemetry> telemetry = ValueNotifier(const Telemetry());
  final ValueNotifier<String?> errorMessage = ValueNotifier(null);

  Future<void> connect(String host, int port) async {
    await disconnect();
    status.value = ConnectionStatus.connecting;
    errorMessage.value = null;

    try {
      final channel = WebSocketChannel.connect(Uri.parse('ws://$host:$port'));
      await channel.ready;
      _channel = channel;
      status.value = ConnectionStatus.connected;

      _subscription = channel.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message as String) as Map<String, dynamic>;
            telemetry.value = Telemetry.fromJson(data);
          } catch (_) {
            // 忽略無法解析的訊息
          }
        },
        onError: (_) {
          status.value = ConnectionStatus.error;
          errorMessage.value = '連線中斷';
        },
        onDone: () {
          if (status.value == ConnectionStatus.connected) {
            status.value = ConnectionStatus.disconnected;
          }
        },
      );
    } catch (e) {
      status.value = ConnectionStatus.error;
      errorMessage.value = '無法連線: $e';
    }
  }

  void sendControl(double x, double y) {
    if (status.value != ConnectionStatus.connected || _channel == null) return;
    _channel!.sink.add(jsonEncode({'x': x, 'y': y}));
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
    status.value = ConnectionStatus.disconnected;
  }
}
