import 'package:flutter/material.dart';

/// 圓形虛擬搖桿。回報的(x, y)皆正規化到[-1, 1]，
/// y軸方向已翻轉成「往上拉為正值」，對應day19 direction_to_force()裡UP指令(fy為正)的施力方向。
class Joystick extends StatefulWidget {
  const Joystick({super.key, required this.onChanged, this.size = 200});

  final void Function(double x, double y) onChanged;
  final double size;

  @override
  State<Joystick> createState() => _JoystickState();
}

class _JoystickState extends State<Joystick> {
  Offset _knobOffset = Offset.zero;

  double get _radius => widget.size / 2;

  void _updateFromLocalPosition(Offset localPosition) {
    final center = Offset(_radius, _radius);
    var delta = localPosition - center;
    final distance = delta.distance;
    if (distance > _radius) {
      delta = delta * (_radius / distance);
    }

    setState(() => _knobOffset = delta);

    final normalizedX = delta.dx / _radius;
    final normalizedY = -delta.dy / _radius; // 螢幕座標往下為正，翻轉成往上為正
    widget.onChanged(normalizedX.clamp(-1.0, 1.0), normalizedY.clamp(-1.0, 1.0));
  }

  void _resetKnob() {
    setState(() => _knobOffset = Offset.zero);
    widget.onChanged(0, 0);
  }

  @override
  Widget build(BuildContext context) {
    final knobSize = widget.size * 0.35;
    return GestureDetector(
      onPanStart: (details) => _updateFromLocalPosition(details.localPosition),
      onPanUpdate: (details) => _updateFromLocalPosition(details.localPosition),
      onPanEnd: (_) => _resetKnob(),
      onPanCancel: _resetKnob,
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white.withValues(alpha: 0.06),
          border: Border.all(color: Colors.white24, width: 2),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Positioned(
              left: _radius - knobSize / 2 + _knobOffset.dx,
              top: _radius - knobSize / 2 + _knobOffset.dy,
              child: Container(
                width: knobSize,
                height: knobSize,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.tealAccent.withValues(alpha: 0.85),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
