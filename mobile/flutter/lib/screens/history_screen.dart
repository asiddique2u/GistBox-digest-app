import 'dart:io';

import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/models/digest_record.dart';
import 'package:gistbox_mobile/screens/digest_result_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.historyStore});

  final DigestHistoryStore historyStore;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<List<DigestRecord>> _history = widget.historyStore.load();

  void _reload() {
    setState(() {
      _history = widget.historyStore.load();
    });
  }

  Future<void> _confirmClear() async {
    final shouldClear = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Clear saved digests?'),
        content: const Text(
          'This removes all saved digest history from this device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Clear history'),
          ),
        ],
      ),
    );
    if (shouldClear != true || !mounted) {
      return;
    }

    try {
      await widget.historyStore.clear();
      if (mounted) {
        setState(() {
          _history = Future.value(<DigestRecord>[]);
        });
      }
    } on FileSystemException {
      _showClearError('Could not clear saved history from this device.');
    } on PlatformException {
      _showClearError('Local storage is unavailable on this device.');
    }
  }

  void _showClearError(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _openRecord(DigestRecord record) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => DigestResultScreen(
          record: record,
          historyStore: widget.historyStore,
        ),
      ),
    );
  }

  String _formatDate(DateTime dateTime) {
    final local = dateTime.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(local);
    final time = MaterialLocalizations.of(
      context,
    ).formatTimeOfDay(TimeOfDay.fromDateTime(local));
    return '$date · $time';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Saved digests')),
    body: SafeArea(
      child: FutureBuilder<List<DigestRecord>>(
        future: _history,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(
                semanticsLabel: 'Loading saved digests',
              ),
            );
          }
          if (snapshot.hasError) {
            return _HistoryMessage(
              icon: Icons.error_outline,
              title: 'Could not load saved digests',
              message: 'Your history could not be read from this device.',
              actionLabel: 'Try again',
              onAction: _reload,
            );
          }

          final records = snapshot.data ?? const <DigestRecord>[];
          if (records.isEmpty) {
            return const _HistoryMessage(
              icon: Icons.bookmarks_outlined,
              title: 'No saved digests yet',
              message: 'Digests you create will be kept here on this device.',
            );
          }

          return Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _confirmClear,
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('Clear history'),
                ),
              ),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  itemCount: records.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final record = records[index];
                    return Card(
                      color: Colors.white,
                      elevation: 0,
                      clipBehavior: Clip.antiAlias,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: const BorderSide(color: Color(0xFFE5E9E3)),
                      ),
                      child: ListTile(
                        title: Text(
                          record.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          '${record.filename ?? record.url}\n${_formatDate(record.savedAt)}',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        isThreeLine: true,
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => _openRecord(record),
                      ),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    ),
  );
}

class _HistoryMessage extends StatelessWidget {
  const _HistoryMessage({
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 36, color: const Color(0xFF2E644D)),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(message, textAlign: TextAlign.center),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: 12),
            FilledButton.tonal(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}
