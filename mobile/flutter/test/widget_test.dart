import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gistbox_mobile/data/gistbox_api.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/gistbox_app.dart';
import 'package:gistbox_mobile/models/digest_record.dart';

void main() {
  testWidgets('creates and saves a digest for a valid study link', (
    tester,
  ) async {
    final repository = _FakeDigestRepository();
    final history = _FakeDigestHistoryStore();
    await tester.pumpWidget(
      GistBoxApp(digestRepository: repository, historyStore: history),
    );

    await tester.enterText(
      find.byType(TextFormField),
      'https://example.edu/lesson',
    );
    await tester.tap(find.text('Create digest'));
    await tester.pumpAndSettle();

    expect(find.text('Sample digest'), findsOneWidget);
    expect(find.text('Saved on this device'), findsOneWidget);
    expect(repository.lastUrl, 'https://example.edu/lesson');
    expect(history.records, hasLength(1));
  });

  testWidgets('offers URL and PDF entry modes', (tester) async {
    await tester.pumpWidget(
      GistBoxApp(
        digestRepository: _FakeDigestRepository(),
        historyStore: _FakeDigestHistoryStore(),
      ),
    );

    expect(find.text('Learn from links and PDFs'), findsOneWidget);
    expect(find.byType(TextFormField), findsOneWidget);

    await tester.tap(find.text('PDF'));
    await tester.pumpAndSettle();

    expect(find.text('Choose a PDF'), findsOneWidget);
  });

  testWidgets('allows a student to clear on-device digest history', (
    tester,
  ) async {
    final history = _FakeDigestHistoryStore()
      ..records.add(
        DigestRecord(
          url: 'https://example.edu/lesson',
          detailLevel: DigestDetailLevel.medium,
          title: 'Saved lesson',
          summary: '- Main idea',
          savedAt: DateTime.utc(2026, 11, 18),
        ),
      );
    await tester.pumpWidget(
      GistBoxApp(
        digestRepository: _FakeDigestRepository(),
        historyStore: history,
      ),
    );

    await tester.tap(find.byTooltip('Open saved digests'));
    await tester.pumpAndSettle();
    expect(find.text('Saved lesson'), findsOneWidget);

    await tester.tap(find.widgetWithText(TextButton, 'Clear history'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Clear history'));
    await tester.pumpAndSettle();

    expect(find.text('No saved digests yet'), findsOneWidget);
    expect(history.records, isEmpty);
  });
}

class _FakeDigestRepository implements DigestRepository {
  String? lastUrl;

  @override
  Future<DigestRecord> digestPdf({
    required String fileName,
    required List<int> bytes,
    required DigestDetailLevel detailLevel,
  }) async => DigestRecord(
    filename: fileName,
    detailLevel: detailLevel,
    title: 'Sample digest',
    summary: '- Sample takeaway',
    savedAt: DateTime.utc(2026, 11, 18),
  );

  @override
  Future<DigestRecord> digestUrl({
    required String url,
    required DigestDetailLevel detailLevel,
  }) async {
    lastUrl = url;
    return DigestRecord(
      url: url,
      detailLevel: detailLevel,
      title: 'Sample digest',
      summary: '- Sample takeaway',
      savedAt: DateTime.utc(2026, 11, 18),
    );
  }
}

class _FakeDigestHistoryStore implements DigestHistoryStore {
  final records = <DigestRecord>[];

  @override
  Future<List<DigestRecord>> load() async => List.of(records);

  @override
  Future<void> clear() async {
    records.clear();
  }

  @override
  Future<void> save(DigestRecord record) async {
    records.add(record);
  }
}
