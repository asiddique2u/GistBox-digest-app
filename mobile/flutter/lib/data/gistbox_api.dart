import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:gistbox_mobile/models/digest_record.dart';
import 'package:http/http.dart' as http;

abstract interface class DigestRepository {
  Future<DigestRecord> digestUrl({
    required String url,
    required DigestDetailLevel detailLevel,
  });

  Future<DigestRecord> digestPdf({
    required String fileName,
    required List<int> bytes,
    required DigestDetailLevel detailLevel,
  });
}

class DigestApiException implements Exception {
  const DigestApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class GistBoxApi implements DigestRepository {
  static const _maxPdfBytes = 10 * 1024 * 1024;

  GistBoxApi({
    required String baseUrl,
    required http.Client client,
    this.requestTimeout = const Duration(seconds: 90),
  }) : _baseUrl = baseUrl,
       _client = client;

  final String _baseUrl;
  final http.Client _client;
  final Duration requestTimeout;

  @override
  Future<DigestRecord> digestUrl({
    required String url,
    required DigestDetailLevel detailLevel,
  }) async {
    final parsedUrl = Uri.tryParse(url);
    if (parsedUrl == null ||
        (parsedUrl.scheme != 'http' && parsedUrl.scheme != 'https') ||
        parsedUrl.host.isEmpty) {
      throw const DigestApiException('Enter a complete HTTP or HTTPS link.');
    }

    final response = await _send(
      () => _client.post(
        _endpoint('/digest'),
        headers: const {'content-type': 'application/json'},
        body: jsonEncode({'url': url, 'detail_level': detailLevel.wireValue}),
      ),
    );
    return _parseDigestResponse(response);
  }

  @override
  Future<DigestRecord> digestPdf({
    required String fileName,
    required List<int> bytes,
    required DigestDetailLevel detailLevel,
  }) async {
    if (!fileName.toLowerCase().endsWith('.pdf')) {
      throw const DigestApiException('Choose a PDF file.');
    }
    if (bytes.isEmpty) {
      throw const DigestApiException('The selected PDF is empty.');
    }
    if (bytes.length > _maxPdfBytes) {
      throw const DigestApiException('Choose a PDF smaller than 10 MB.');
    }

    final request = http.MultipartRequest('POST', _endpoint('/digest/pdf'))
      ..fields['detail_level'] = detailLevel.wireValue
      ..files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: fileName),
      );
    final response = await _send(() async {
      final streamed = await _client.send(request);
      return http.Response.fromStream(streamed);
    });
    return _parseDigestResponse(response);
  }

  Uri _endpoint(String path) {
    final base = Uri.tryParse(_baseUrl);
    if (base == null ||
        !base.hasScheme ||
        base.host.isEmpty ||
        (base.scheme != 'http' && base.scheme != 'https')) {
      throw const DigestApiException('The GistBox API URL is not configured.');
    }
    return base.resolve(path);
  }

  Future<http.Response> _send(Future<http.Response> Function() send) async {
    try {
      return await send().timeout(requestTimeout);
    } on TimeoutException {
      throw const DigestApiException(
        'The request took too long. Check your connection and try again.',
      );
    } on SocketException {
      throw const DigestApiException(
        'Could not reach GistBox. Check your connection and try again.',
      );
    } on http.ClientException {
      throw const DigestApiException(
        'Could not reach GistBox. Check your connection and try again.',
      );
    }
  }

  DigestRecord _parseDigestResponse(http.Response response) {
    Object? decoded;
    try {
      decoded = jsonDecode(response.body);
    } on FormatException {
      throw const DigestApiException(
        'GistBox returned an unreadable response. Please try again.',
      );
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = decoded is Map<String, dynamic> ? decoded['detail'] : null;
      throw DigestApiException(
        detail is String && detail.isNotEmpty
            ? detail
            : 'GistBox could not create this digest. Please try again.',
      );
    }
    if (decoded is! Map<String, dynamic>) {
      throw const DigestApiException(
        'GistBox returned an unreadable response. Please try again.',
      );
    }

    try {
      return DigestRecord.fromApiJson(decoded);
    } on FormatException {
      throw const DigestApiException(
        'GistBox returned an incomplete digest. Please try again.',
      );
    }
  }
}
