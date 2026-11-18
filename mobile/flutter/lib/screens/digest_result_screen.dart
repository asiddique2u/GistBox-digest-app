import 'dart:io';

import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/models/digest_record.dart';

class DigestResultScreen extends StatefulWidget {
  const DigestResultScreen({
    super.key,
    required this.record,
    required this.historyStore,
    this.initialSaveError,
  });

  final DigestRecord record;
  final DigestHistoryStore historyStore;
  final String? initialSaveError;

  @override
  State<DigestResultScreen> createState() => _DigestResultScreenState();
}

class _DigestResultScreenState extends State<DigestResultScreen> {
  late String? _saveError = widget.initialSaveError;
  bool _isSaving = false;

  MarkdownStyleSheet _markdownStyleSheet(BuildContext context) {
    final theme = Theme.of(context);
    final body = theme.textTheme.bodyMedium;
    return MarkdownStyleSheet(
      a: TextStyle(color: theme.colorScheme.primary),
      p: body,
      pPadding: EdgeInsets.zero,
      code: body?.copyWith(fontFamily: 'monospace'),
      h1: theme.textTheme.headlineSmall,
      h1Padding: EdgeInsets.zero,
      h2: theme.textTheme.titleLarge,
      h2Padding: EdgeInsets.zero,
      h3: theme.textTheme.titleMedium,
      h3Padding: EdgeInsets.zero,
      h4: theme.textTheme.bodyLarge,
      h4Padding: EdgeInsets.zero,
      h5: theme.textTheme.bodyLarge,
      h5Padding: EdgeInsets.zero,
      h6: theme.textTheme.bodyLarge,
      h6Padding: EdgeInsets.zero,
      em: const TextStyle(fontStyle: FontStyle.italic),
      strong: const TextStyle(fontWeight: FontWeight.bold),
      del: const TextStyle(decoration: TextDecoration.lineThrough),
      blockquote: body,
      img: body,
      checkbox: body?.copyWith(color: theme.colorScheme.primary),
      blockSpacing: 8,
      listIndent: 24,
      listBullet: body,
      listBulletPadding: const EdgeInsets.only(right: 4),
      tableHead: const TextStyle(fontWeight: FontWeight.w600),
      tableBody: body,
      tableBorder: TableBorder.all(color: theme.colorScheme.outlineVariant),
      blockquotePadding: const EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 4,
      ),
      blockquoteDecoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(3),
        border: Border(
          left: BorderSide(color: theme.colorScheme.primary, width: 3),
        ),
      ),
      codeblockPadding: const EdgeInsets.all(8),
      codeblockDecoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Future<void> _retrySave() async {
    setState(() => _isSaving = true);
    String? error;
    try {
      await widget.historyStore.save(widget.record);
    } on FileSystemException {
      error = 'Could not save this digest on your device.';
    } on FormatException {
      error = 'Saved history could not be updated.';
    } on PlatformException {
      error = 'Local storage is unavailable on this device.';
    }
    if (mounted) {
      setState(() {
        _isSaving = false;
        _saveError = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Digest')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Text(
            widget.record.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: const Color(0xFF1B2C25),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            widget.record.source,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Color(0xFF536159)),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              Chip(label: Text('${widget.record.detailLevel.label} digest')),
              if (_saveError == null)
                const Chip(
                  avatar: Icon(Icons.bookmark_added_outlined, size: 18),
                  label: Text('Saved on this device'),
                ),
            ],
          ),
          if (_saveError != null) ...[
            const SizedBox(height: 8),
            MaterialBanner(
              content: Text(_saveError!),
              leading: const Icon(Icons.warning_amber_outlined),
              actions: [
                TextButton(
                  onPressed: _isSaving ? null : _retrySave,
                  child: Text(_isSaving ? 'Saving…' : 'Retry'),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          // Avoid network requests from image links in untrusted digest text.
          MarkdownBody(
            data: widget.record.summary,
            selectable: true,
            styleSheet: _markdownStyleSheet(context),
            imageBuilder: (_, _, alt) => alt == null || alt.isEmpty
                ? const SizedBox.shrink()
                : Text(alt),
          ),
        ],
      ),
    ),
  );
}
