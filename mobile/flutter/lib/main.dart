import 'package:flutter/foundation.dart';
import 'package:material_ui/material_ui.dart';
import 'package:gistbox_mobile/data/gistbox_api.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/gistbox_app.dart';
import 'package:http/http.dart' as http;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  const apiBaseUrl = String.fromEnvironment(
    'GISTBOX_API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
  if (kReleaseMode && !apiBaseUrl.startsWith('https://')) {
    throw StateError(
      'Set GISTBOX_API_BASE_URL to the production HTTPS API URL.',
    );
  }

  runApp(
    GistBoxApp(
      digestRepository: GistBoxApi(baseUrl: apiBaseUrl, client: http.Client()),
      historyStore: JsonDigestHistoryStore(),
    ),
  );
}
