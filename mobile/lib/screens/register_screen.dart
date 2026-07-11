import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../utils/input_filters.dart';
import 'patient_home_screen.dart';
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = {
    'username': TextEditingController(),
    'password': TextEditingController(),
    'passwordConfirm': TextEditingController(),
    'email': TextEditingController(),
    'nom': TextEditingController(),
    'prenom': TextEditingController(),
    'date_naissance': TextEditingController(text: '1990-01-01'),
    'telephone': TextEditingController(),
  };
  String _sexe = 'M';
  bool _loading = false;
  String? _error;

  Future<void> _register() async {
    final phone = (_form['telephone'] as TextEditingController).text.trim();
    final password = (_form['password'] as TextEditingController).text;
    final passwordConfirm = (_form['passwordConfirm'] as TextEditingController).text;
    if (phone.isEmpty) {
      setState(() => _error = 'Le numéro de téléphone est obligatoire');
      return;
    }
    if (password.length < 10) {
      setState(() => _error = 'Le mot de passe doit contenir au moins 10 caractères');
      return;
    }
    if (password != passwordConfirm) {
      setState(() => _error = 'Les mots de passe ne correspondent pas');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final payload = {
      'username': (_form['username'] as TextEditingController).text.trim(),
      'password': password,
      'email': (_form['email'] as TextEditingController).text.trim(),
      'nom': (_form['nom'] as TextEditingController).text.trim(),
      'prenom': (_form['prenom'] as TextEditingController).text.trim(),
      'date_naissance': (_form['date_naissance'] as TextEditingController).text,
      'sexe': _sexe,
      'telephone': phone,
      'consentement_traitement': true,
    };
    final data = await ApiService.registerPatient(payload);
    if (!mounted) return;
    setState(() => _loading = false);
    if (data != null) {
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const PatientHomeScreen()),
        (_) => false,
      );
    } else {
      setState(() => _error = 'Inscription impossible — vérifiez les champs');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Inscription patient')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          TextField(
            controller: _form['nom'] as TextEditingController,
            inputFormatters: [SghlInputFilters.lettersOnly],
            decoration: const InputDecoration(labelText: 'Nom', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _form['prenom'] as TextEditingController,
            inputFormatters: [SghlInputFilters.lettersOnly],
            decoration: const InputDecoration(labelText: 'Prénom', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _form['username'] as TextEditingController,
            inputFormatters: [SghlInputFilters.alnumOnly],
            decoration: const InputDecoration(labelText: 'Identifiant', border: OutlineInputBorder()),
          ),          const SizedBox(height: 12),
          TextField(controller: _form['email'] as TextEditingController, decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(
            controller: _form['telephone'] as TextEditingController,
            keyboardType: TextInputType.phone,
            inputFormatters: [SghlInputFilters.phoneOnly],
            decoration: const InputDecoration(
              labelText: 'Téléphone mobile *',
              hintText: '+242 066967236',
              border: OutlineInputBorder(),
            ),
          ),          const SizedBox(height: 12),
          TextField(controller: _form['password'] as TextEditingController, obscureText: true, decoration: const InputDecoration(labelText: 'Mot de passe (10+ car.)', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _form['date_naissance'] as TextEditingController, decoration: const InputDecoration(labelText: 'Date naissance (AAAA-MM-JJ)', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _sexe,
            decoration: const InputDecoration(labelText: 'Sexe', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'M', child: Text('Masculin')),
              DropdownMenuItem(value: 'F', child: Text('Féminin')),
            ],
            onChanged: (v) => setState(() => _sexe = v ?? 'M'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _register,
            child: Text(_loading ? 'Inscription…' : 'Créer mon compte'),
          ),
        ],
      ),
    );
  }
}
