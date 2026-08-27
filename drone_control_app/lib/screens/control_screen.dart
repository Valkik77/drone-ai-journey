import 'dart:async';

import 'package:flutter/material.dart';

import '../services/drone_socket_service.dart';
import '../widgets/joystick.dart';
import '../widgets/position_radar.dart';

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
    _service.cameraFrame.addListener(_onServiceChanged);
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
    _service.cameraFrame.removeListener(_onServiceChanged);
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
    final cameraFrame = _service.cameraFrame.value;
    final connected = status == ConnectionStatus.connected;

    return Scaffold(
      appBar: AppBar(title: const Text('無人機模擬搖控器')),
      body: SafeArea(
        child: SingleChildScrollView(
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
              // 攝影機參考畫面:鏡頭沒有真的裝在無人機上,畫面不會隨模擬位置移動,純粹是測試時的參考
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: AspectRatio(
                  aspectRatio: 4 / 3,
                  child: Container(
                    color: Colors.black26,
                    child: cameraFrame != null
                        ? Image.memory(
                            cameraFrame,
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                          )
                        : Center(
                            child: Text(
                              connected ? '等待攝影機畫面...' : '連線後顯示攝影機畫面(僅供參考,不隨模擬移動)',
                              style: Theme.of(context).textTheme.bodySmall,
                              textAlign: TextAlign.center,
                            ),
                          ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      // 雷達圖:把X/Y畫成面板上的一個點,不用只靠數字腦補方向
                      PositionRadar(x: telemetry.x, y: telemetry.y),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _TelemetryValue(label: 'X (左右)', value: telemetry.x),
                          _TelemetryValue(label: 'Y (前後)', value: telemetry.y),
                          _TelemetryValue(label: 'Z (高度)', value: telemetry.z),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Joystick(
                      size: 220,
                      onChanged: (x, y) {
                        _joystickX = x;
                        _joystickY = y;
                      },
                    ),
                    Positioned(
                      top: -20,
                      child: Text('前 (Y+)', style: Theme.of(context).textTheme.labelSmall),
                    ),
                    Positioned(
                      bottom: -20,
                      child: Text('後 (Y-)', style: Theme.of(context).textTheme.labelSmall),
                    ),
                    Positioned(
                      left: -20,
                      child: Text('左\n(X-)', style: Theme.of(context).textTheme.labelSmall),
                    ),
                    Positioned(
                      right: -20,
                      child: Text('右\n(X+)', style: Theme.of(context).textTheme.labelSmall),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
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
