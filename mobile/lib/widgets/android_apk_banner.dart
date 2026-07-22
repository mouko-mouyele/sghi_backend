import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_links.dart';

/// Bandeau visible sur la version Web — lien de téléchargement APK Android.
class AndroidApkBanner extends StatelessWidget {
  const AndroidApkBanner({super.key});

  Future<void> _downloadApk() async {
    final uri = Uri.parse(AppLinks.apkDownloadUrl);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      throw Exception('Impossible d\'ouvrir le lien de téléchargement');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb) return const SizedBox.shrink();

    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        border: Border.all(color: Colors.green.shade400),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.android, color: Colors.green.shade800, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Application Android',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.green.shade900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Installez SGHL sur votre téléphone Android (APK officiel, ~15 Mo). '
            'Autorisez « sources inconnues » si Android le demande.',
            style: TextStyle(fontSize: 12, color: Colors.green.shade900),
          ),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: _downloadApk,
            icon: const Icon(Icons.download),
            label: const Text('Télécharger l\'APK Android'),
            style: FilledButton.styleFrom(
              backgroundColor: Colors.green.shade700,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            AppLinks.apkDownloadUrl,
            style: TextStyle(fontSize: 10, color: cs.outline),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
