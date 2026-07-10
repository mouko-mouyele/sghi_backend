import 'package:flutter/foundation.dart';

/// URL API selon la plateforme.
/// Chrome / Web → localhost Django
/// Android émulateur → 10.0.2.2
class ApiConfig {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return 'http://10.0.2.2:8000/api/v1';
  }

  /// Origine serveur Django (sans /api/v1) pour médias et liens publics.
  static String get serverOrigin => baseUrl.replaceAll('/api/v1', '');

  static String absoluteUrl(String path) {
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    if (path.startsWith('/')) return '$serverOrigin$path';
    return '$serverOrigin/$path';
  }
}
