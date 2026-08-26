import 'package:flutter/material.dart';

/// 把模擬無人機的X/Y位置畫成雷達圖，取代單看數字才能理解方向的問題。
/// 呼應day19影像上疊加的十字準心：中心十字 + 座標軸標籤(前後左右) + 目前位置的點。
class PositionRadar extends StatelessWidget {
  const PositionRadar({
    super.key,
    required this.x,
    required this.y,
    this.size = 160,
    this.range = 3.0,
  });

  final double x;
  final double y;
  final double size;
  final double range; // 對應到面板邊緣的座標值(公尺)，超過就貼齊邊緣顯示

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size + 20,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned(
            top: 0,
            child: Text('前 (Y+)', style: Theme.of(context).textTheme.labelSmall),
          ),
          Positioned(
            bottom: 0,
            child: Text('後 (Y-)', style: Theme.of(context).textTheme.labelSmall),
          ),
          Positioned(
            left: 0,
            top: 10,
            bottom: 10,
            child: Align(
              alignment: Alignment.centerLeft,
              child: RotatedBox(
                quarterTurns: 3,
                child: Text('左 (X-)', style: Theme.of(context).textTheme.labelSmall),
              ),
            ),
          ),
          Positioned(
            right: 0,
            top: 10,
            bottom: 10,
            child: Align(
              alignment: Alignment.centerRight,
              child: RotatedBox(
                quarterTurns: 1,
                child: Text('右 (X+)', style: Theme.of(context).textTheme.labelSmall),
              ),
            ),
          ),
          Positioned(
            top: 20,
            child: CustomPaint(
              size: Size(size - 40, size - 40),
              painter: _RadarPainter(x: x, y: y, range: range),
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  _RadarPainter({required this.x, required this.y, required this.range});

  final double x;
  final double y;
  final double range;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    final borderPaint = Paint()
      ..color = Colors.white24
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawRect(Offset.zero & size, borderPaint);

    final crosshairPaint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 1;
    canvas.drawLine(Offset(center.dx, 0), Offset(center.dx, size.height), crosshairPaint);
    canvas.drawLine(Offset(0, center.dy), Offset(size.width, center.dy), crosshairPaint);

    // X對應畫面水平軸(右為正)，Y對應畫面垂直軸,但畫布往下為正,
    // 所以Y要取負號才會是「往上=前=Y+」,跟Joystick的方向定義一致。
    final normalizedX = (x / range).clamp(-1.0, 1.0);
    final normalizedY = (y / range).clamp(-1.0, 1.0);
    final dotOffset = Offset(
      center.dx + normalizedX * (size.width / 2 - 6),
      center.dy - normalizedY * (size.height / 2 - 6),
    );

    final isClamped = x.abs() > range || y.abs() > range;
    final dotPaint = Paint()..color = isClamped ? Colors.orangeAccent : Colors.tealAccent;
    canvas.drawCircle(dotOffset, 6, dotPaint);
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) {
    return oldDelegate.x != x || oldDelegate.y != y || oldDelegate.range != range;
  }
}
