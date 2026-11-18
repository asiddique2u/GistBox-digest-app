import 'dart:convert';
import 'dart:io';

import 'package:gistbox_mobile/models/digest_record.dart';
import 'package:path_provider/path_provider.dart';

abstract interface class DigestHistoryStore {
  Future<List<DigestRecord>> load();

  Future<void> save(DigestRecord record);

  Future<void> clear();
}

class JsonDigestHistoryStore implements DigestHistoryStore {
  JsonDigestHistoryStore({Future<Directory> Function()? directoryProvider})
    : _directoryProvider =
          directoryProvider ?? getApplicationDocumentsDirectory;

  static const _schemaVersion = 1;
  final Future<Directory> Function() _directoryProvider;

  Future<File> _historyFile() async {
    final directory = await _directoryProvider();
    return File(
      '${directory.path}${Platform.pathSeparator}digest_history.json',
    );
  }

  @override
  Future<List<DigestRecord>> load() async {
    final file = await _historyFile();
    final backup = File('${file.path}.bak');
    final source = await file.exists()
        ? file
        : await backup.exists()
        ? backup
        : null;
    if (source == null) {
      return [];
    }

    final decoded = jsonDecode(await source.readAsString());
    if (decoded is! Map<String, dynamic> ||
        decoded['version'] != _schemaVersion ||
        decoded['items'] is! List<dynamic>) {
      throw const FormatException('The saved digest history is not valid.');
    }

    final records =
        (decoded['items'] as List<dynamic>).map((entry) {
            if (entry is! Map<String, dynamic>) {
              throw const FormatException('A saved digest entry is not valid.');
            }
            return DigestRecord.fromStoredJson(entry);
          }).toList()
          ..sort((first, second) => second.savedAt.compareTo(first.savedAt));
    return records;
  }

  @override
  Future<void> save(DigestRecord record) async {
    final file = await _historyFile();
    final records = await load();
    records
      ..add(record)
      ..sort((first, second) => second.savedAt.compareTo(first.savedAt));
    await _write(file, records);
  }

  @override
  Future<void> clear() async {
    await _write(await _historyFile(), const []);
  }

  Future<void> _write(File file, List<DigestRecord> records) async {
    await file.parent.create(recursive: true);

    final temporary = File('${file.path}.tmp');
    final backup = File('${file.path}.bak');
    await temporary.writeAsString(
      jsonEncode({
        'version': _schemaVersion,
        'items': records.map((item) => item.toStoredJson()).toList(),
      }),
      flush: true,
    );

    if (await backup.exists()) {
      await backup.delete();
    }
    if (await file.exists()) {
      await file.rename(backup.path);
    }
    try {
      await temporary.rename(file.path);
    } catch (_) {
      if (await backup.exists() && !await file.exists()) {
        await backup.rename(file.path);
      }
      rethrow;
    }
    if (await backup.exists()) {
      await backup.delete();
    }
  }
}
