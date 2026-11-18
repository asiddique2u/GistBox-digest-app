enum DigestDetailLevel { short, medium, detailed }

extension DigestDetailLevelLabel on DigestDetailLevel {
  String get wireValue => name;

  String get label => switch (this) {
    DigestDetailLevel.short => 'Short',
    DigestDetailLevel.medium => 'Medium',
    DigestDetailLevel.detailed => 'Detailed',
  };
}

class DigestRecord {
  factory DigestRecord({
    String? url,
    String? filename,
    required DigestDetailLevel detailLevel,
    required String title,
    required String summary,
    required DateTime savedAt,
  }) {
    if ((url == null) == (filename == null) ||
        (url != null && url.isEmpty) ||
        (filename != null && filename.isEmpty) ||
        title.trim().isEmpty ||
        summary.trim().isEmpty) {
      throw ArgumentError('A digest must have exactly one non-empty source.');
    }
    return DigestRecord._(
      url: url,
      filename: filename,
      detailLevel: detailLevel,
      title: title,
      summary: summary,
      savedAt: savedAt,
    );
  }

  const DigestRecord._({
    this.url,
    this.filename,
    required this.detailLevel,
    required this.title,
    required this.summary,
    required this.savedAt,
  });

  factory DigestRecord.fromApiJson(Map<String, Object?> json) {
    final url = json['url'];
    final filename = json['filename'];
    if (!((url is String && filename == null) ||
        (filename is String && url == null))) {
      throw const FormatException(
        'The digest response must include exactly one source.',
      );
    }

    final detailLevel = DigestDetailLevel.values.where(
      (level) => level.wireValue == json['detail_level'],
    );
    final title = json['title'];
    final summary = json['summary'];
    if (detailLevel.isEmpty ||
        title is! String ||
        title.trim().isEmpty ||
        summary is! String ||
        summary.trim().isEmpty ||
        (url is String && url.isEmpty) ||
        (filename is String && filename.isEmpty)) {
      throw const FormatException('The digest response is incomplete.');
    }

    return DigestRecord(
      url: url is String ? url : null,
      filename: filename is String ? filename : null,
      detailLevel: detailLevel.first,
      title: title,
      summary: summary,
      savedAt: DateTime.now().toUtc(),
    );
  }

  factory DigestRecord.fromStoredJson(Map<String, Object?> json) {
    final source = json['source'];
    final url = source is Map<String, Object?> ? source['url'] : null;
    final filename = source is Map<String, Object?> ? source['filename'] : null;
    final detailLevel = DigestDetailLevel.values.where(
      (level) => level.wireValue == json['detail_level'],
    );
    final title = json['title'];
    final summary = json['summary'];
    final savedAt = json['saved_at'];

    if (!((url is String && filename == null) ||
            (filename is String && url == null)) ||
        detailLevel.isEmpty ||
        title is! String ||
        title.trim().isEmpty ||
        summary is! String ||
        summary.trim().isEmpty ||
        (url is String && url.isEmpty) ||
        (filename is String && filename.isEmpty) ||
        savedAt is! String) {
      throw const FormatException('A saved digest entry is invalid.');
    }

    return DigestRecord(
      url: url is String ? url : null,
      filename: filename is String ? filename : null,
      detailLevel: detailLevel.first,
      title: title,
      summary: summary,
      savedAt: DateTime.parse(savedAt),
    );
  }

  final String? url;
  final String? filename;
  final DigestDetailLevel detailLevel;
  final String title;
  final String summary;
  final DateTime savedAt;

  String get source => url ?? filename!;

  Map<String, Object?> toStoredJson() => {
    'source': {'url': url, 'filename': filename},
    'detail_level': detailLevel.wireValue,
    'title': title,
    'summary': summary,
    'saved_at': savedAt.toUtc().toIso8601String(),
  };

  @override
  bool operator ==(Object other) =>
      other is DigestRecord &&
      other.url == url &&
      other.filename == filename &&
      other.detailLevel == detailLevel &&
      other.title == title &&
      other.summary == summary &&
      other.savedAt == savedAt;

  @override
  int get hashCode =>
      Object.hash(url, filename, detailLevel, title, summary, savedAt);
}
