import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:gistbox_mobile/data/gistbox_api.dart';
import 'package:gistbox_mobile/models/digest_record.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('sends URL and detail level and parses the digest response', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/digest');
      expect(jsonDecode(request.body), {
        'url': 'https://example.edu/lesson',
        'detail_level': 'short',
      });
      return http.Response(
        jsonEncode({
          'url': 'https://example.edu/lesson',
          'detail_level': 'short',
          'title': 'Lesson notes',
          'summary': '- Main idea',
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);
    final result = await api.digestUrl(
      url: 'https://example.edu/lesson',
      detailLevel: DigestDetailLevel.short,
    );

    expect(result.title, 'Lesson notes');
    expect(result.url, 'https://example.edu/lesson');
    client.close();
  });

  test('sends a PDF as multipart form data', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/digest/pdf');
      expect(
        request.headers['content-type'],
        startsWith('multipart/form-data; boundary='),
      );
      final body = utf8.decode(request.bodyBytes);
      expect(body, contains('name="detail_level"'));
      expect(body, contains('name="file"; filename="notes.pdf"'));
      expect(body, contains('%PDF'));
      return http.Response(
        jsonEncode({
          'filename': 'notes.pdf',
          'detail_level': 'detailed',
          'title': 'Notes',
          'summary': '- Concepts',
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);
    final result = await api.digestPdf(
      fileName: 'notes.pdf',
      bytes: [0x25, 0x50, 0x44, 0x46],
      detailLevel: DigestDetailLevel.detailed,
    );

    expect(result.filename, 'notes.pdf');
    client.close();
  });

  test('rejects PDFs larger than the backend limit', () async {
    final client = MockClient((_) async => http.Response('{}', 200));
    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);

    await expectLater(
      api.digestPdf(
        fileName: 'large.pdf',
        bytes: List.filled(10 * 1024 * 1024 + 1, 0),
        detailLevel: DigestDetailLevel.detailed,
      ),
      throwsA(
        isA<DigestApiException>().having(
          (error) => error.message,
          'message',
          'Choose a PDF smaller than 10 MB.',
        ),
      ),
    );
    client.close();
  });

  test('surfaces the backend error detail', () async {
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({'detail': 'The source could not be extracted.'}),
        422,
        headers: {'content-type': 'application/json'},
      ),
    );
    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);

    await expectLater(
      api.digestUrl(
        url: 'https://example.edu/lesson',
        detailLevel: DigestDetailLevel.detailed,
      ),
      throwsA(
        isA<DigestApiException>().having(
          (error) => error.message,
          'message',
          'The source could not be extracted.',
        ),
      ),
    );
    client.close();
  });

  test('rejects a successful response with ambiguous source fields', () async {
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({
          'url': 'https://example.edu/lesson',
          'filename': 'notes.pdf',
          'detail_level': 'short',
          'title': 'Lesson notes',
          'summary': '- Main idea',
        }),
        200,
        headers: {'content-type': 'application/json'},
      ),
    );
    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);

    await expectLater(
      api.digestUrl(
        url: 'https://example.edu/lesson',
        detailLevel: DigestDetailLevel.short,
      ),
      throwsA(isA<DigestApiException>()),
    );
    client.close();
  });

  test('rejects non-HTTP URL schemes before requesting a digest', () async {
    final client = MockClient((_) async => http.Response('{}', 200));
    final api = GistBoxApi(baseUrl: 'https://api.example.test', client: client);

    await expectLater(
      api.digestUrl(
        url: 'file:///private/notes.pdf',
        detailLevel: DigestDetailLevel.short,
      ),
      throwsA(
        isA<DigestApiException>().having(
          (error) => error.message,
          'message',
          'Enter a complete HTTP or HTTPS link.',
        ),
      ),
    );
    client.close();
  });
}
