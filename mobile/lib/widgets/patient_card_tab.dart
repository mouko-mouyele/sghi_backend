import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../utils/pdf_download.dart';

class PatientCardTab extends StatefulWidget {
  const PatientCardTab({super.key});

  @override
  State<PatientCardTab> createState() => _PatientCardTabState();
}

class _PatientCardTabState extends State<PatientCardTab> {
  bool _loading = true;
  bool _downloading = false;
  Map<String, dynamic>? _profile;
  Map<String, dynamic>? _cardInfo;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    final results = await Future.wait<Map<String, dynamic>?>([
      ApiService.patientProfile(),
      ApiService.patientCardPdfLink(),
    ]);
    if (!mounted) return;
    setState(() {
      _profile = results[0];
      _cardInfo = results[1];
      _loading = false;
    });
  }

  Future<void> _downloadPdf() async {
    setState(() { _downloading = true; _error = null; });
    final result = await ApiService.downloadPatientCardPdf();
    if (!mounted) return;
    if (result.error != null) {
      setState(() { _downloading = false; _error = result.error; });
      return;
    }
    try {
      downloadPdfBytes(result.bytes!, result.filename!);
      final link = await ApiService.patientCardPdfLink();
      if (link != null) setState(() => _cardInfo = link);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Carte ${result.filename} téléchargée')),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  Future<void> _openUrl(String? url) async {
    if (url == null || url.isEmpty) return;
    final full = ApiConfig.absoluteUrl(url);
    final uri = Uri.parse(full);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _copyText(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copié dans le presse-papiers')));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    final p = _profile ?? {};
    final qrUrl = _cardInfo?['qr_url']?.toString() ?? '';
    final pdfUrl = _cardInfo?['pdf_url']?.toString() ?? _cardInfo?['media_url']?.toString() ?? '';

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: const Color(0xFFE0F2F1),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.badge, color: Theme.of(context).colorScheme.primary, size: 32),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text('Carte patient CHU', style: Theme.of(context).textTheme.titleMedium),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Le PDF contient votre nom, prénom, e-mail et adresse, avec un QR code scannable par le personnel médical.',
                    style: TextStyle(fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const CircleAvatar(
                backgroundColor: Color(0xFF0D9488),
                child: Icon(Icons.person, color: Colors.white),
              ),
              title: Text('${p['prenom'] ?? ''} ${p['nom'] ?? ''}'.trim()),
              subtitle: Text(
                'Dossier ${p['numero_dossier'] ?? '—'}\n${p['email'] ?? ''}\n${p['adresse'] ?? '—'}',
              ),
              isThreeLine: true,
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _downloading ? null : _downloadPdf,
            icon: _downloading
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.download),
            label: Text(_downloading ? 'Génération…' : 'Télécharger ma carte PDF'),
          ),
          if (pdfUrl.isNotEmpty) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _openUrl(pdfUrl),
              icon: const Icon(Icons.picture_as_pdf),
              label: const Text('Ouvrir le PDF en ligne'),
            ),
          ],
          const SizedBox(height: 16),
          Text('QR code médical', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'En scannant le QR de votre carte, le personnel accède à votre dossier médical complet (hospitalisation, ordonnances, labo…).',
                    style: TextStyle(fontSize: 13),
                  ),
                  if (qrUrl.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    SelectableText(qrUrl, style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _copyText(qrUrl),
                            icon: const Icon(Icons.copy, size: 18),
                            label: const Text('Copier le lien'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton.tonalIcon(
                            onPressed: () => _openUrl(qrUrl),
                            icon: const Icon(Icons.open_in_new, size: 18),
                            label: const Text('Ouvrir'),
                          ),
                        ),
                      ],
                    ),
                  ] else
                    const Padding(
                      padding: EdgeInsets.only(top: 12),
                      child: Text('Générez d\'abord votre carte PDF pour obtenir le lien QR.'),
                    ),
                ],
              ),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ],
      ),
    );
  }
}
