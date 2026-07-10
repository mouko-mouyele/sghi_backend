import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'patient_home_screen.dart';
import 'doctor_home_screen.dart';
import 'register_screen.dart';

enum LoginProfile { patient, medecin }

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  LoginProfile _profile = LoginProfile.patient;
  final _user = TextEditingController(text: 'patient.demo');
  final _pass = TextEditingController();
  final _mfaCode = TextEditingController();
  bool _loading = false;
  bool? _serverOk;
  String? _error;
  bool _obscure = true;
  bool _mfaStep = false;
  String _pendingToken = '';
  String _mfaHint = '';
  String _pendingRole = '';
  int _mfaSecondsLeft = 0;
  bool _mfaExpired = false;
  Timer? _mfaTimer;

  @override
  void dispose() {
    _mfaTimer?.cancel();
    _user.dispose();
    _pass.dispose();
    _mfaCode.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _pass.text = 'Patient@2026!';
    _updateDemoCredentials();
    _checkServer();
  }

  Future<void> _checkServer() async {
    final ok = await ApiService.pingServer();
    if (mounted) setState(() => _serverOk = ok);
  }

  void _updateDemoCredentials() {
    if (_profile == LoginProfile.patient) {
      _user.text = 'patient.demo';
      _pass.text = 'Patient@2026!';
    } else {
      _user.text = 'dr.martin';
      _pass.text = 'Medecin@2026!';
    }
  }

  Future<void> _goHome(String role) async {
    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => role == 'MEDECIN' ? const DoctorHomeScreen() : const PatientHomeScreen(),
      ),
    );
  }

  void _startMfaTimer(int seconds) {
    _mfaTimer?.cancel();
    _mfaExpired = false;
    _mfaSecondsLeft = seconds;
    _mfaTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      setState(() {
        if (_mfaSecondsLeft <= 1) {
          _mfaSecondsLeft = 0;
          _mfaExpired = true;
          _error = 'Code expiré — validité de 5 minutes dépassée. Reconnectez-vous.';
          t.cancel();
        } else {
          _mfaSecondsLeft--;
        }
      });
    });
  }

  String _mfaCountdownLabel() {
    final m = _mfaSecondsLeft ~/ 60;
    final s = _mfaSecondsLeft % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  Future<void> _login() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await ApiService.login(_user.text.trim(), _pass.text);
      if (!mounted) return;

      if (result.needsMfa) {
        setState(() {
          _mfaStep = true;
          _pendingToken = result.pendingToken;
          _mfaHint = result.mfaHint;
          _pendingRole = result.role;
        });
        _startMfaTimer(result.mfaExpiresIn);
        return;
      }

      if (!result.ok) {
        setState(() {
          _error = result.error;
          _serverOk = result.isNetworkError ? false : _serverOk;
        });
        return;
      }

      final role = result.data!['role'] as String? ?? '';
      final expectedPatient = _profile == LoginProfile.patient;
      if (expectedPatient && role != 'PATIENT') {
        setState(() => _error = 'Ce compte n\'est pas un profil patient');
        await ApiService.logout();
        return;
      }
      if (!expectedPatient && role != 'MEDECIN') {
        setState(() => _error = 'Ce compte n\'est pas un profil médecin');
        await ApiService.logout();
        return;
      }
      await _goHome(role);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _verifyMfa() async {
    if (_mfaExpired) {
      setState(() => _error = 'Code expiré. Reconnectez-vous pour un nouveau code.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await ApiService.loginMfa(_pendingToken, _mfaCode.text.trim());
      if (!mounted) return;
      if (!result.ok) {
        setState(() => _error = result.error ?? 'Code invalide');
        return;
      }
      final role = result.data!['role'] as String? ?? _pendingRole;
      await _goHome(role);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _backToPassword() {
    _mfaTimer?.cancel();
    setState(() {
      _mfaStep = false;
      _mfaExpired = false;
      _mfaSecondsLeft = 0;
      _pendingToken = '';
      _mfaCode.clear();
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.local_hospital, size: 56, color: cs.primary),
                  const SizedBox(height: 12),
                  Text(
                    _mfaStep ? 'Code par email' : 'SGHL Mobile',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _mfaStep ? _mfaHint : 'CHU Brazzaville — Patient & Médecin',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                  if (_serverOk != null && !_mfaStep) ...[
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          _serverOk! ? Icons.cloud_done : Icons.cloud_off,
                          size: 16,
                          color: _serverOk! ? Colors.green : Colors.red,
                        ),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            _serverOk!
                                ? 'Serveur connecté'
                                : 'Serveur arrêté — lancez python manage.py runserver',
                            style: TextStyle(
                              fontSize: 12,
                              color: _serverOk! ? Colors.green.shade700 : Colors.red.shade700,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 28),
                  if (!_mfaStep) ...[
                    Text('Je me connecte en tant que', style: Theme.of(context).textTheme.labelLarge),
                    const SizedBox(height: 10),
                    SegmentedButton<LoginProfile>(
                      segments: const [
                        ButtonSegment(value: LoginProfile.patient, label: Text('Patient'), icon: Icon(Icons.person)),
                        ButtonSegment(value: LoginProfile.medecin, label: Text('Médecin'), icon: Icon(Icons.medical_services)),
                      ],
                      selected: {_profile},
                      onSelectionChanged: (s) {
                        setState(() {
                          _profile = s.first;
                          _updateDemoCredentials();
                          _error = null;
                        });
                      },
                    ),
                    const SizedBox(height: 24),
                    TextField(
                      controller: _user,
                      decoration: const InputDecoration(labelText: 'Identifiant', border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _pass,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'Mot de passe',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                  ] else ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                      decoration: BoxDecoration(
                        color: _mfaExpired
                            ? Colors.red.shade50
                            : (_mfaSecondsLeft <= 60 ? Colors.amber.shade50 : Colors.green.shade50),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        _mfaExpired
                            ? 'Code expiré — reconnectez-vous'
                            : 'Code valide encore ${_mfaCountdownLabel()}',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: _mfaExpired
                              ? Colors.red.shade800
                              : (_mfaSecondsLeft <= 60 ? Colors.amber.shade900 : Colors.green.shade800),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _mfaCode,
                      enabled: !_mfaExpired,
                      keyboardType: TextInputType.number,
                      maxLength: 6,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 24, letterSpacing: 8),
                      decoration: const InputDecoration(
                        labelText: 'Code à 6 chiffres',
                        border: OutlineInputBorder(),
                        counterText: '',
                      ),
                    ),
                  ],
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: TextStyle(color: cs.error)),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: (_loading || (_mfaStep && _mfaExpired)) ? null : (_mfaStep ? _verifyMfa : _login),
                    child: _loading
                        ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_mfaStep ? (_mfaExpired ? 'Code expiré' : 'Valider le code') : 'Se connecter'),
                  ),
                  if (_mfaStep)
                    TextButton(
                      onPressed: _backToPassword,
                      child: Text(_mfaExpired ? 'Recevoir un nouveau code' : 'Retour'),
                    ),
                  if (!_mfaStep && _profile == LoginProfile.patient) ...[
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RegisterScreen())),
                      child: const Text('Créer un compte patient'),
                    ),
                  ],
                  if (!_mfaStep) ...[
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: cs.primaryContainer.withOpacity(0.4),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        _profile == LoginProfile.patient
                            ? 'Démo : patient.demo / Patient@2026!\nCode MFA → email (valide 5 min)'
                            : 'Démo : dr.martin / Medecin@2026!\nCode MFA → boîte mail hôpital (5 min)',
                        style: const TextStyle(fontSize: 12),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
