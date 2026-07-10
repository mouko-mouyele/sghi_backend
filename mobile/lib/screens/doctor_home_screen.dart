import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/doctor_pharmacy_tab.dart';
import 'login_screen.dart';

class DoctorHomeScreen extends StatefulWidget {
  const DoctorHomeScreen({super.key});
  @override
  State<DoctorHomeScreen> createState() => _DoctorHomeScreenState();
}

class _DoctorHomeScreenState extends State<DoctorHomeScreen> {
  int _index = 0;
  List<dynamic> _rdv = [];
  List<dynamic> _patients = [];
  Map<String, dynamic>? _me;
  bool _loading = true;
  final _search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.doctorAppointments(),
      ApiService.doctorPatients(search: _search.text.trim()),
      ApiService.me(),
    ]);
    if (!mounted) return;
    setState(() {
      _rdv = results[0] as List<dynamic>;
      _patients = results[1] as List<dynamic>;
      _me = results[2] as Map<String, dynamic>?;
      _loading = false;
    });
  }

  Future<void> _logout() async {
    await ApiService.logout();
    if (!mounted) return;
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  String _fmtDate(dynamic iso) {
    if (iso == null) return '—';
    try {
      return DateTime.parse(iso.toString()).toLocal().toString().substring(0, 16).replaceFirst('T', ' ');
    } catch (_) {
      return iso.toString();
    }
  }

  Color _statutColor(String? statut) {
    switch (statut) {
      case 'CONFIRME':
        return Colors.green;
      case 'PLANIFIE':
        return Colors.blue;
      case 'ANNULE':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Espace Médecin'),
        backgroundColor: const Color(0xFF1E40AF),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          IconButton(icon: const Icon(Icons.logout), onPressed: _logout),
        ],
      ),
      body: IndexedStack(
              index: _index,
              children: [_buildRdvTab(), _buildPatientsTab(), const DoctorPharmacyTab(), _buildProfileTab()],
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.calendar_today), label: 'Agenda'),
          NavigationDestination(icon: Icon(Icons.people), label: 'Patients'),
          NavigationDestination(icon: Icon(Icons.local_pharmacy), label: 'Pharma'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profil'),
        ],
      ),
    );
  }

  Widget _buildRdvTab() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final upcoming = List<dynamic>.from(_rdv)
      ..sort((a, b) => (a['date_heure'] ?? '').toString().compareTo((b['date_heure'] ?? '').toString()));

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          color: Colors.blue.shade50,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(Icons.event, color: Color(0xFF1E40AF), size: 36),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${upcoming.length} rendez-vous', style: Theme.of(context).textTheme.titleLarge),
                    const Text('Agenda synchronisé CHU'),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text('Mes rendez-vous', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (upcoming.isEmpty) const Card(child: ListTile(title: Text('Aucun rendez-vous'))),
        ...upcoming.map((r) => Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: _statutColor(r['statut']?.toString()),
                  child: const Icon(Icons.person, color: Colors.white, size: 18),
                ),
                title: Text(r['motif']?.toString() ?? 'Consultation'),
                subtitle: Text(_fmtDate(r['date_heure'])),
                trailing: Chip(
                  label: Text(r['statut']?.toString() ?? '', style: const TextStyle(fontSize: 10)),
                  padding: EdgeInsets.zero,
                ),
              ),
            )),
      ],
    );
  }

  Widget _buildPatientsTab() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _search,
          decoration: InputDecoration(
            labelText: 'Rechercher un patient',
            border: const OutlineInputBorder(),
            suffixIcon: IconButton(icon: const Icon(Icons.search), onPressed: _load),
          ),
          onSubmitted: (_) => _load(),
        ),
        const SizedBox(height: 16),
        Text('${_patients.length} patient(s)', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        ..._patients.map((p) => Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: const Color(0xFF0D9488),
                  child: Text('${p['prenom']?[0] ?? 'P'}', style: const TextStyle(color: Colors.white)),
                ),
                title: Text('${p['prenom'] ?? ''} ${p['nom'] ?? ''}'.trim()),
                subtitle: Text('Dossier ${p['numero_dossier'] ?? ''} · ${p['telephone'] ?? '—'}'),
                trailing: Text(p['sexe']?.toString() ?? '', style: const TextStyle(fontSize: 12)),
              ),
            )),
        if (_patients.isEmpty) const Card(child: ListTile(title: Text('Aucun patient trouvé'))),
      ],
    );
  }

  Widget _buildProfileTab() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final m = _me ?? {};
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: const Color(0xFF1E40AF),
                  child: Text(
                    '${m['first_name']?[0] ?? 'D'}${m['last_name']?[0] ?? 'r'}',
                    style: const TextStyle(color: Colors.white, fontSize: 28),
                  ),
                ),
                const SizedBox(height: 16),
                Text('Dr ${m['first_name'] ?? ''} ${m['last_name'] ?? ''}'.trim(),
                    style: Theme.of(context).textTheme.titleLarge),
                Text(m['specialty']?.toString() ?? 'Médecine', style: TextStyle(color: Colors.grey[600])),
                const SizedBox(height: 8),
                Text(m['email']?.toString() ?? ''),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Card(
          child: ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Application mobile SGHL'),
            subtitle: Text('Profils disponibles : Patient et Médecin.\nPour les autres rôles, utilisez le portail web.'),
          ),
        ),
      ],
    );
  }
}
