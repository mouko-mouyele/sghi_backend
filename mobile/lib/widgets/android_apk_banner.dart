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
            'Téléchargez SGHL Mobile (~35 Mo, Android 5.0+). '
            'Compatible Infinix Smart et autres téléphones Android.',
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
          const SizedBox(height: 10),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text(
              '« Application non installée » ?',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.green.shade900,
              ),
            ),
            children: [
              Text(
                '1. Désinstallez toute ancienne version SGHL Mobile\n'
                '2. Infinix (XOS) : Paramètres → Confidentialité → '
                'Autoriser l\'installation d\'apps de sources inconnues → Chrome + Fichiers\n'
                '3. Désactivez temporairement Phone Master / XSecurity si l\'install est bloquée\n'
                '4. Retéléchargez l\'APK en Wi-Fi, puis ouvrez-le depuis l\'app Fichiers\n'
                '5. Play Protect : Paramètres → Google → Play Protect → désactiver temporairement',
                style: TextStyle(fontSize: 11, color: Colors.green.shade900, height: 1.4),
              ),
            ],
          ),
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
