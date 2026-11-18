import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:gistbox_mobile/data/gistbox_api.dart';
import 'package:gistbox_mobile/data/json_digest_history_store.dart';
import 'package:gistbox_mobile/models/digest_record.dart';
import 'package:gistbox_mobile/screens/digest_result_screen.dart';
import 'package:gistbox_mobile/screens/history_screen.dart';

enum _SourceMode { link, pdf }

class DigestHomeScreen extends StatefulWidget {
  const DigestHomeScreen({
    super.key,
    required this.digestRepository,
    required this.historyStore,
  });

  final DigestRepository digestRepository;
  final DigestHistoryStore historyStore;

  @override
  State<DigestHomeScreen> createState() => _DigestHomeScreenState();
}

class _DigestHomeScreenState extends State<DigestHomeScreen> {
  static const _maxPdfBytes = 10 * 1024 * 1024;
  final _formKey = GlobalKey<FormState>();
  final _urlController = TextEditingController();
  _SourceMode _sourceMode = _SourceMode.link;
  DigestDetailLevel _detailLevel = DigestDetailLevel.detailed;
  List<int>? _pdfBytes;
  String? _pdfName;
  String? _errorMessage;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _pickPdf() async {
    setState(() => _errorMessage = null);
    try {
      final file = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: const ['pdf'],
      );
      if (!mounted || file == null) {
        return;
      }

      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setState(() => _errorMessage = 'Choose a PDF file.');
        return;
      }
      final fileSize = await file.length();
      if (fileSize == null) {
        setState(() => _errorMessage = 'The selected PDF could not be read.');
        return;
      }
      if (fileSize > _maxPdfBytes) {
        setState(() => _errorMessage = 'Choose a PDF smaller than 10 MB.');
        return;
      }
      final bytes = await file.readAsBytes();
      if (bytes.length > _maxPdfBytes) {
        setState(() => _errorMessage = 'Choose a PDF smaller than 10 MB.');
        return;
      }
      if (bytes.isEmpty) {
        setState(() => _errorMessage = 'The selected PDF could not be read.');
        return;
      }

      if (!mounted) {
        return;
      }
      setState(() {
        _pdfBytes = bytes;
        _pdfName = file.name;
      });
    } on FileSystemException {
      if (mounted) {
        setState(() => _errorMessage = 'The selected PDF could not be read.');
      }
    } on PlatformException {
      if (mounted) {
        setState(() => _errorMessage = 'The file picker could not be opened.');
      }
    }
  }

  Future<void> _createDigest() async {
    if (_isSubmitting) {
      return;
    }
    if (_sourceMode == _SourceMode.link &&
        !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    if (_sourceMode == _SourceMode.pdf && _pdfBytes == null) {
      setState(() => _errorMessage = 'Choose a PDF before creating a digest.');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    DigestRecord record;
    try {
      record = _sourceMode == _SourceMode.link
          ? await widget.digestRepository.digestUrl(
              url: _urlController.text.trim(),
              detailLevel: _detailLevel,
            )
          : await widget.digestRepository.digestPdf(
              fileName: _pdfName!,
              bytes: _pdfBytes!,
              detailLevel: _detailLevel,
            );
    } on DigestApiException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = error.message);
      }
      return;
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }

    if (!mounted) {
      return;
    }
    if (_sourceMode == _SourceMode.pdf) {
      setState(() {
        _pdfBytes = null;
        _pdfName = null;
      });
    }

    String? saveError;
    try {
      await widget.historyStore.save(record);
    } on FileSystemException {
      saveError = 'Digest created, but it could not be saved on this device.';
    } on FormatException {
      saveError = 'Digest created, but saved history could not be updated.';
    } on PlatformException {
      saveError = 'Digest created, but local storage is unavailable.';
    }
    if (!mounted) {
      return;
    }

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => DigestResultScreen(
          record: record,
          historyStore: widget.historyStore,
          initialSaveError: saveError,
        ),
      ),
    );
  }

  String? _validateUrl(String? value) {
    final text = value?.trim() ?? '';
    final uri = Uri.tryParse(text);
    if (uri == null ||
        (uri.scheme != 'http' && uri.scheme != 'https') ||
        uri.host.isEmpty) {
      return 'Enter a complete HTTP or HTTPS link.';
    }
    return null;
  }

  Future<void> _openHistory() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => HistoryScreen(historyStore: widget.historyStore),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text(
        'GistBox',
        style: TextStyle(fontWeight: FontWeight.w700),
      ),
      actions: [
        IconButton(
          tooltip: 'Open saved digests',
          onPressed: _openHistory,
          icon: const Icon(Icons.bookmarks_outlined),
        ),
      ],
    ),
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Learn from links and PDFs',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: const Color(0xFF1B2C25),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Turn course material into clear, useful takeaways.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: const Color(0xFF536159),
                  ),
                ),
                const SizedBox(height: 24),
                Card(
                  color: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: const BorderSide(color: Color(0xFFE5E9E3)),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SegmentedButton<_SourceMode>(
                          segments: const [
                            ButtonSegment(
                              value: _SourceMode.link,
                              label: Text('Link'),
                              icon: Icon(Icons.link),
                            ),
                            ButtonSegment(
                              value: _SourceMode.pdf,
                              label: Text('PDF'),
                              icon: Icon(Icons.picture_as_pdf_outlined),
                            ),
                          ],
                          selected: {_sourceMode},
                          onSelectionChanged: _isSubmitting
                              ? null
                              : (selection) => setState(() {
                                  _sourceMode = selection.first;
                                  _errorMessage = null;
                                }),
                        ),
                        const SizedBox(height: 20),
                        if (_sourceMode == _SourceMode.link)
                          Form(
                            key: _formKey,
                            child: TextFormField(
                              controller: _urlController,
                              keyboardType: TextInputType.url,
                              textInputAction: TextInputAction.done,
                              autocorrect: false,
                              validator: _validateUrl,
                              decoration: const InputDecoration(
                                labelText: 'Study link',
                                hintText: 'https://example.edu/topic',
                                prefixIcon: Icon(Icons.link),
                              ),
                            ),
                          )
                        else
                          _buildPdfPicker(),
                        const SizedBox(height: 20),
                        DropdownButtonFormField<DigestDetailLevel>(
                          initialValue: _detailLevel,
                          decoration: const InputDecoration(
                            labelText: 'Digest depth',
                          ),
                          items: DigestDetailLevel.values
                              .map(
                                (level) => DropdownMenuItem(
                                  value: level,
                                  child: Text(level.label),
                                ),
                              )
                              .toList(),
                          onChanged: _isSubmitting
                              ? null
                              : (value) {
                                  if (value != null) {
                                    setState(() => _detailLevel = value);
                                  }
                                },
                        ),
                        if (_errorMessage != null) ...[
                          const SizedBox(height: 16),
                          Semantics(
                            liveRegion: true,
                            child: Text(
                              _errorMessage!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: _isSubmitting ? null : _createDigest,
                          icon: _isSubmitting
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.auto_awesome_outlined),
                          label: Text(
                            _isSubmitting
                                ? 'Creating digest…'
                                : 'Create digest',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'PDFs are sent to GistBox for processing and are not kept in your on-device history.',
                  style: TextStyle(color: Color(0xFF748078), fontSize: 13),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );

  Widget _buildPdfPicker() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      OutlinedButton.icon(
        onPressed: _isSubmitting ? null : _pickPdf,
        icon: const Icon(Icons.upload_file_outlined),
        label: Text(_pdfName == null ? 'Choose a PDF' : 'Choose another PDF'),
      ),
      if (_pdfName != null) ...[
        const SizedBox(height: 10),
        Text(
          _pdfName!,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: Color(0xFF536159)),
        ),
      ],
      const SizedBox(height: 6),
      const Text(
        'PDF only · Up to 10 MB',
        style: TextStyle(color: Color(0xFF748078), fontSize: 13),
      ),
    ],
  );
}
