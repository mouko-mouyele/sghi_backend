import 'package:flutter/foundation.dart';

/// URL API selon l'environnement.
///
/// - **Production** (Render, APK release) : `https://sghi-backend.onrender.com/api/v1`
/// - **Dev web** : `http://127.0.0.1:8000/api/v1`
/// - **Dev Android émulateur** : `http://10.0.2.2:8000/api/v1`
///
/// Override au build : `--dart-define=SGHL_API_URL=https://...`
class ApiConfig {
  static const String _productionApi = 'https://sghi-backend.onrender.com/api/v1';

  static String get baseUrl {
    const fromDefine = String.fromEnvironment('SGHL_API_URL');
    if (fromDefine.isNotEmpty) return fromDefine;

    if (kReleaseMode) return _productionApi;

    if (kIsWeb) return 'http://127.0.0.1:8000/api/v1';
    return 'http://10.0.2.2:8000/api/v1';
  }

  static String get serverOrigin => baseUrl.replaceAll('/api/v1', '');

  static String absoluteUrl(String path) {
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    if (path.startsWith('/')) return '$serverOrigin$path';
    return '$serverOrigin/$path';
  }
}
