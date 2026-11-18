import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/models/digest_record.dart';

void main() {
  late Directory directory;

  setUp(() async {
    directory = await Directory.systemTemp.createTemp('gistbox-history-test');
  });

  tearDown(() async {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  });

  test('persists digests so a new store can load them', () async {
    final store = JsonDigestHistoryStore(
      directoryProvider: () async => directory,
    );
    final record = DigestRecord(
      url: 'https://example.edu/lesson',
      detailLevel: DigestDetailLevel.medium,
      title: 'Lesson notes',
      summary: '- Main idea',
      savedAt: DateTime.utc(2026, 11, 18),
    );

    await store.save(record);
    final reloaded = await JsonDigestHistoryStore(
      directoryProvider: () async => directory,
    ).load();

    expect(reloaded, [record]);
  });

  test('reports corrupt history instead of treating it as empty', () async {
    await File(
      '${directory.path}${Platform.pathSeparator}digest_history.json',
    ).writeAsString('{broken');
    final store = JsonDigestHistoryStore(
      directoryProvider: () async => directory,
    );

    await expectLater(store.load(), throwsFormatException);
  });

  test('clears saved history', () async {
    final store = JsonDigestHistoryStore(
      directoryProvider: () async => directory,
    );
    await store.save(
      DigestRecord(
        filename: 'notes.pdf',
        detailLevel: DigestDetailLevel.short,
        title: 'Notes',
        summary: '- Main idea',
        savedAt: DateTime.utc(2026, 11, 18),
      ),
    );

    await store.clear();

    expect(await store.load(), isEmpty);
  });
}
