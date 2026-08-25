import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:drone_control_app/main.dart';

void main() {
  testWidgets('顯示連線欄與搖桿', (WidgetTester tester) async {
    await tester.pumpWidget(const DroneControlApp());

    expect(find.text('無人機模擬搖控器'), findsOneWidget);
    expect(find.text('連線'), findsOneWidget);
    expect(find.byType(TextField), findsNWidgets(2));
  });
}
