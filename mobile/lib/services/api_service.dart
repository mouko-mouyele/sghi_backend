import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

class LoginResult {
  final Map<String, dynamic>? data;
  final String? error;
  final bool isNetworkError;
  final bool requiresMfa;
  final String pendingToken;
  final String mfaHint;
  final String mfaScreenCode;
  final String role;
  final int mfaExpiresIn;

  const LoginResult._({
    this.data,
    this.error,
    this.isNetworkError = false,
    this.requiresMfa = false,
    this.pendingToken = '',
    this.mfaHint = '',
    this.mfaScreenCode = '',
    this.role = '',
    this.mfaExpiresIn = 300,
  });

  factory LoginResult.success(Map<String, dynamic> data) => LoginResult._(data: data);

  factory LoginResult.mfaRequired({
    required String pendingToken,
    required String mfaHint,
    required String role,
    String mfaScreenCode = '',
    int mfaExpiresIn = 300,
  }) =>
      LoginResult._(
        requiresMfa: true,
        pendingToken: pendingToken,
        mfaHint: mfaHint,
        mfaScreenCode: mfaScreenCode,
        role: role,
        mfaExpiresIn: mfaExpiresIn,
      );

  factory LoginResult.failure(String error, {bool isNetworkError = false}) =>
      LoginResult._(error: error, isNetworkError: isNetworkError);

  bool get ok => data != null;
  bool get needsMfa => requiresMfa;
}

class ApiService {
  static String get baseUrl => ApiConfig.baseUrl;
  static const Duration _timeout = Duration(seconds: 8);

  static Future<bool> pingServer() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/sante')).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<Map<String, String>> _headers({bool auth = true}) async {
    final h = {'Content-Type': 'application/json', 'Accept': 'application/json'};
    if (auth) {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');
      if (token != null) h['Authorization'] = 'Bearer $token';
    }
    return h;
  }

  static Future<LoginResult> login(String username, String password) async {
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/auth/login'),
            headers: await _headers(auth: false),
            body: jsonEncode({'username': username, 'password': password}),
          )
          .timeout(_timeout);

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        if (data['requires_mfa'] == true) {
          return LoginResult.mfaRequired(
            pendingToken: data['pending_token'] as String? ?? '',
            mfaHint: data['mfa_hint'] as String? ?? 'Consultez votre boîte mail',
            mfaScreenCode: data['mfa_dev_code'] as String? ?? '',
            role: data['role'] as String? ?? '',
            mfaExpiresIn: data['mfa_expires_in'] as int? ?? 300,
          );
        }
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', data['access_token'] as String);
        await prefs.setString('refresh_token', data['refresh_token'] as String);
        await prefs.setString('role', data['role'] as String? ?? '');
        await prefs.setString('user_id', '${data['user_id'] ?? ''}');
        return LoginResult.success(data);
      }

      if (res.statusCode == 400) {
        try {
          final body = jsonDecode(res.body);
          if (body is Map && body['detail'] != null) {
            return LoginResult.failure(body['detail'].toString());
          }
        } catch (_) {}
      }

      if (res.statusCode == 401) {
        return LoginResult.failure('Identifiants invalides');
      }

      try {
        final body = jsonDecode(res.body);
        if (body is Map && body['detail'] != null) {
          return LoginResult.failure(body['detail'].toString());
        }
      } catch (_) {}
      return LoginResult.failure('Erreur serveur (${res.statusCode})');
    } on TimeoutException {
      return LoginResult.failure(
        'Serveur trop lent ou arrêté.\nLancez : python manage.py runserver',
        isNetworkError: true,
      );
    } on http.ClientException {
      return LoginResult.failure(
        'Impossible de joindre l\'API ($baseUrl).\n'
        '1. Démarrez le backend : python manage.py runserver\n'
        '2. Vérifiez seed_demo si les comptes n\'existent pas',
        isNetworkError: true,
      );
    } catch (e) {
      return LoginResult.failure('Erreur : $e');
    }
  }

  static Future<LoginResult> loginMfa(String pendingToken, String code) async {
    final digits = code.replaceAll(RegExp(r'\D'), '');
    final normalized = digits.padLeft(6, '0');
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/auth/login/mfa'),
            headers: await _headers(auth: false),
            body: jsonEncode({'pending_token': pendingToken.trim(), 'code': normalized}),
          )
          .timeout(_timeout);

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', data['access_token'] as String);
        await prefs.setString('refresh_token', data['refresh_token'] as String);
        await prefs.setString('role', data['role'] as String? ?? '');
        await prefs.setString('user_id', '${data['user_id'] ?? ''}');
        return LoginResult.success(data);
      }
      if (res.statusCode == 401) {
        try {
          final body = jsonDecode(res.body);
          if (body is Map && body['detail'] != null) {
            return LoginResult.failure(body['detail'].toString());
          }
        } catch (_) {}
        return LoginResult.failure('Code invalide ou expiré (5 minutes)');
      }
      return LoginResult.failure('Erreur serveur (${res.statusCode})');
    } on TimeoutException {
      return LoginResult.failure('Serveur trop lent', isNetworkError: true);
    } catch (e) {
      return LoginResult.failure('Erreur : $e');
    }
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  static Future<String?> getRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('role');
  }

  static Future<Map<String, dynamic>?> me() async {
    final res = await http.get(Uri.parse('$baseUrl/auth/me'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    return null;
  }

  static Future<Map<String, dynamic>?> registerPatient(Map<String, dynamic> payload) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/register/patient'),
      headers: await _headers(auth: false),
      body: jsonEncode(payload),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('access_token', data['access_token'] as String);
      await prefs.setString('refresh_token', data['refresh_token'] as String);
      await prefs.setString('role', data['role'] as String? ?? 'PATIENT');
      return data;
    }
    return null;
  }

  // ── Patient ─────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> patientDashboard() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/tableau-de-bord'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    return null;
  }

  static Future<List<dynamic>> patientAppointments() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/rendez-vous'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<Map<String, dynamic>?> patientCarePlan() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/plan-soins'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    return null;
  }

  static Future<List<dynamic>> patientLabResults() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/resultats-labo'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<Map<String, dynamic>?> patientProfile() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/moi'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    return null;
  }

  static Future<List<dynamic>> patientInvoices() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/factures'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<List<dynamic>> pharmacyCatalog({String q = '', String categorie = ''}) async {
    final uri = Uri.parse('$baseUrl/patient/pharmacie/medicaments').replace(queryParameters: {
      if (q.isNotEmpty) 'q': q,
      if (categorie.isNotEmpty) 'categorie': categorie,
    });
    final res = await http.get(uri, headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<List<dynamic>> pharmacyRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/pharmacie/demandes'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<({Map<String, dynamic>? data, String? error})> submitPharmacyRequest({
    required List<Map<String, dynamic>> lignes,
    String notes = '',
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/patient/pharmacie/demandes'),
      headers: await _headers(),
      body: jsonEncode({'lignes': lignes, if (notes.isNotEmpty) 'notes': notes}),
    );
    if (res.statusCode == 200) {
      return (data: jsonDecode(res.body) as Map<String, dynamic>, error: null);
    }
    return (data: null, error: _errorBody(res));
  }

  static Future<({Map<String, dynamic>? data, String? error})> initMobileMoney(
    int invoiceId, {
    required String numeroMobile,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/patient/factures/$invoiceId/mobile-money/initier'),
            headers: await _headers(),
            body: jsonEncode({'numero_mobile': numeroMobile.trim()}),
          )
          .timeout(_timeout);
      if (res.statusCode == 200) {
        return (data: jsonDecode(res.body) as Map<String, dynamic>, error: null);
      }
      return (data: null, error: _errorBody(res));
    } on TimeoutException {
      return (data: null, error: 'Délai dépassé — vérifiez le serveur');
    } catch (e) {
      return (data: null, error: 'Erreur réseau : $e');
    }
  }

  static Future<({Map<String, dynamic>? data, String? error})> confirmMobileMoney(
    int invoiceId, {
    required int transactionId,
    required String codePush,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/patient/factures/$invoiceId/mobile-money/confirmer'),
            headers: await _headers(),
            body: jsonEncode({'transaction_id': transactionId, 'code_push': codePush.trim()}),
          )
          .timeout(_timeout);
      if (res.statusCode == 200) {
        return (data: jsonDecode(res.body) as Map<String, dynamic>, error: null);
      }
      return (data: null, error: _errorBody(res));
    } on TimeoutException {
      return (data: null, error: 'Délai dépassé');
    } catch (e) {
      return (data: null, error: 'Erreur réseau : $e');
    }
  }

  static Future<({Map<String, dynamic>? data, String? error})> approveMobileMoney(
    int transactionId, {
    required String numeroMobile,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/patient/mobile-money/$transactionId/approuver'),
            headers: await _headers(),
            body: jsonEncode({'numero_mobile': numeroMobile.trim()}),
          )
          .timeout(_timeout);
      if (res.statusCode == 200) {
        return (data: jsonDecode(res.body) as Map<String, dynamic>, error: null);
      }
      return (data: null, error: _errorBody(res));
    } on TimeoutException {
      return (data: null, error: 'Délai dépassé');
    } catch (e) {
      return (data: null, error: 'Erreur réseau : $e');
    }
  }

  static Future<Map<String, dynamic>?> mobileMoneyStatus(int transactionId) async {
    try {
      final res = await http
          .get(
            Uri.parse('$baseUrl/patient/mobile-money/$transactionId/statut'),
            headers: await _headers(),
          )
          .timeout(_timeout);
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return null;
  }

  static Future<List<dynamic>> availableDoctors() async {
    try {
      final res = await http
          .get(Uri.parse('$baseUrl/medecins/disponibles'), headers: await _headers())
          .timeout(_timeout);
      if (res.statusCode == 200) return jsonDecode(res.body) as List;
    } catch (_) {}
    return [];
  }

  static Future<List<dynamic>> doctorBusySlots(int medecinId, String jour) async {
    try {
      final uri = Uri.parse('$baseUrl/medecins/$medecinId/creneaux').replace(queryParameters: {'jour': jour});
      final res = await http.get(uri, headers: await _headers()).timeout(_timeout);
      if (res.statusCode == 200) return jsonDecode(res.body) as List;
    } catch (_) {}
    return [];
  }

  static Future<({Map<String, dynamic>? data, String? error})> bookAppointment({
    required int medecinId,
    required String dateHeure,
    required String motif,
    int dureeMinutes = 30,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$baseUrl/rendez-vous'),
            headers: await _headers(),
            body: jsonEncode({
              'medecin_id': medecinId,
              'date_heure': dateHeure,
              'motif': motif,
              'duree_minutes': dureeMinutes,
            }),
          )
          .timeout(_timeout);
      if (res.statusCode == 200) {
        return (data: jsonDecode(res.body) as Map<String, dynamic>, error: null);
      }
      return (data: null, error: _errorBody(res));
    } on TimeoutException {
      return (data: null, error: 'Délai dépassé — serveur injoignable');
    } catch (e) {
      return (data: null, error: 'Erreur réseau : $e');
    }
  }

  static Future<({bool ok, String? error})> cancelAppointment(int rdvId) async {
    try {
      final res = await http
          .delete(Uri.parse('$baseUrl/patient/rendez-vous/$rdvId'), headers: await _headers())
          .timeout(_timeout);
      if (res.statusCode == 200) return (ok: true, error: null);
      return (ok: false, error: _errorBody(res));
    } catch (e) {
      return (ok: false, error: 'Erreur : $e');
    }
  }

  static Future<Map<String, dynamic>?> patientCardPdfLink() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/carte-pdf/lien'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    return null;
  }

  static Future<({List<int>? bytes, String? filename, String? error})> downloadPatientCardPdf() async {
    final res = await http.get(Uri.parse('$baseUrl/patient/carte-pdf'), headers: await _headers());
    if (res.statusCode == 200) {
      final cd = res.headers['content-disposition'] ?? '';
      final match = RegExp(r'filename="([^"]+)"').firstMatch(cd);
      final filename = match?.group(1) ?? 'carte-patient.pdf';
      return (bytes: res.bodyBytes, filename: filename, error: null);
    }
    return (bytes: null, filename: null, error: _errorBody(res));
  }

  static String _errorBody(http.Response res) {
    try {
      final body = jsonDecode(res.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        if (d is List) {
          return d.map((e) => e is Map ? (e['msg'] ?? e.toString()) : e.toString()).join(' · ');
        }
        return d.toString();
      }
    } catch (_) {}
    return 'Erreur ${res.statusCode}';
  }

  // ── Médecin ─────────────────────────────────────────────────────────────

  static Future<List<dynamic>> doctorAppointments() async {
    final res = await http.get(Uri.parse('$baseUrl/rendez-vous'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<List<dynamic>> doctorPatients({String search = ''}) async {
    final uri = Uri.parse('$baseUrl/patients').replace(queryParameters: {
      'page': '1',
      'page_size': '30',
      if (search.isNotEmpty) 'search': search,
    });
    final res = await http.get(uri, headers: await _headers());
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      return data['items'] as List? ?? [];
    }
    return [];
  }

  static Future<List<dynamic>> staffMedications({String q = '', String categorie = ''}) async {
    final uri = Uri.parse('$baseUrl/pharmacie/medicaments').replace(queryParameters: {
      if (q.isNotEmpty) 'q': q,
      if (categorie.isNotEmpty) 'categorie': categorie,
    });
    final res = await http.get(uri, headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<List<dynamic>> staffPharmacyStocks() async {
    final res = await http.get(Uri.parse('$baseUrl/pharmacie/stocks'), headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }

  static Future<List<dynamic>> staffPharmacyRequests({String statut = ''}) async {
    final uri = Uri.parse('$baseUrl/pharmacie/demandes').replace(queryParameters: {
      if (statut.isNotEmpty) 'statut': statut,
    });
    final res = await http.get(uri, headers: await _headers());
    if (res.statusCode == 200) return jsonDecode(res.body) as List;
    return [];
  }
}
