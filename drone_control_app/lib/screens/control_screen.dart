import 'dart:async';

import 'package:flutter/material.dart';

import '../services/drone_socket_service.dart';
import '../widgets/joystick.dart';

class ControlScreen extends StatefulWidget {
  const ControlScreen({super.key});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  final _service = DroneSocketService();
  final _hostController = TextEditingController(text: '192.168.0.10');
  final _portController = TextEditingController(text: '8765');

  double _joystickX = 0;
  double _joystickY = 0;
  Timer? _sendTimer;

  @override
  void initState() {
    super.initState();
    _service.status.addListener(_onServiceChanged);
    _service.telemetry.addListener(_onServiceChanged);
    _sendTimer = Timer.periodic(const Duration(milliseconds: 50), (_) {
      _service.sendControl(_joystickX, _joystickY);
    });
  }

  void _onServiceChanged() => setState(() {});

  Future<void> _connect() async {
    final host = _hostController.text.trim();
    final port = int.tryParse(_portController.text.trim()) ?? 8765;
    if (host.isEmpty) return;
    await _service.connect(host, port);
  }

  @override
  void dispose() {
    _sendTimer?.cancel();
    _service.status.removeListener(_onServiceChanged);
    _service.telemetry.removeListener(_onServiceChanged);
    _service.disconnect();
    _hostController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Color _statusColor(ConnectionStatus status) {
    switch (status) {
      case ConnectionStatus.connected:
        return Colors.greenAccent;
      case ConnectionStatus.connecting:
        return Colors.amberAccent;
      case ConnectionStatus.error:
        return Colors.redAccent;
      case ConnectionStatus.disconnected:
        return Colors.white38;
    }
  }

  String _statusLabel(ConnectionStatus status) {
    switch (status) {
      case ConnectionStatus.connected:
        return '已連線';
      case ConnectionStatus.connecting:
        return '連線中...';
      case ConnectionStatus.error:
        return '連線錯誤';
      case ConnectionStatus.disconnected:
        return '未連線';
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = _service.status.value;
    final telemetry = _service.telemetry.value;
    final connected = status == ConnectionStatus.connected;

    return Scaffold(
      appBar: AppBar(title: const Text('無人機模擬搖控器')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: TextField(
                      controller: _hostController,
                      enabled: !connected,
                      decoration: const InputDecoration(labelText: '伺服器IP'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: TextField(
                      controller: _portController,
                      enabled: !connected,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Port'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: connected ? _service.disconnect : _connect,
                    child: Text(connected ? '中斷' : '連線'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _statusColor(status),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(_statusLabel(status)),
                  if (_service.errorMessage.value != null) ...[
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _service.errorMessage.value!,
                        style: const TextStyle(color: Colors.redAccent),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 24),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _TelemetryValue(label: 'X', value: telemetry.x),
                      _TelemetryValue(label: 'Y', value: telemetry.y),
                      _TelemetryValue(label: 'Z (高度)', value: telemetry.z),
                    ],
                  ),
                ),
              ),
              const Spacer(),
              Joystick(
                size: 220,
                onChanged: (x, y) {
                  _joystickX = x;
                  _joystickY = y;
                },
              ),
              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }
}

class _TelemetryValue extends StatelessWidget {
  const _TelemetryValue({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label, style: Theme.of(context).textTheme.labelMedium),
        Text(
          value.toStringAsFixed(2),
          style: Theme.of(context).textTheme.titleLarge,
        ),
      ],
    );
  }
}
