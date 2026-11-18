import 'package:material_ui/material_ui.dart';
import 'package:gistbox_mobile/data/gistbox_api.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/screens/digest_home_screen.dart';

class GistBoxApp extends StatelessWidget {
  const GistBoxApp({
    super.key,
    required this.digestRepository,
    required this.historyStore,
  });

  final DigestRepository digestRepository;
  final DigestHistoryStore historyStore;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'GistBox',
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF2E644D),
        surface: const Color(0xFFFFFFFF),
      ),
      scaffoldBackgroundColor: const Color(0xFFF5F6F2),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFFF5F6F2),
        foregroundColor: Color(0xFF1B2C25),
        centerTitle: false,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFFE5E9E3)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFFE5E9E3)),
        ),
      ),
    ),
    home: DigestHomeScreen(
      digestRepository: digestRepository,
      historyStore: historyStore,
    ),
  );
}
