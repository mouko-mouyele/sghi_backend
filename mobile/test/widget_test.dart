import 'package:flutter_test/flutter_test.dart';
import 'package:sghl_mobile/main.dart';

void main() {
  testWidgets('Affiche le splash SGHL', (WidgetTester tester) async {
    await tester.pumpWidget(const SghlApp());
    await tester.pump();
    expect(find.text('SGHL Mobile'), findsOneWidget);
  });
}
