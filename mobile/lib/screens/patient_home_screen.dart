import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/patient_pharmacy_tab.dart';
import '../widgets/patient_billing_tab.dart';
import '../widgets/patient_card_tab.dart';
import '../widgets/patient_appointments_tab.dart';
import '../utils/format_utils.dart';
import 'login_screen.dart';

class PatientHomeScreen extends StatefulWidget {
  const PatientHomeScreen({super.key});
  @override
  State<PatientHomeScreen> createState() => _PatientHomeScreenState();
}

class _PatientHomeScreenState extends State<PatientHomeScreen> {
  int _index = 0;
  bool _openPaymentOnBilling = false;
  Map<String, dynamic>? _dash;
  Map<String, dynamic>? _care;
  List<dynamic> _lab = [];
  Map<String, dynamic>? _me;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.patientDashboard(),
      ApiService.patientCarePlan(),
      ApiService.patientLabResults(),
      ApiService.me(),
    ]);
    if (!mounted) return;
    setState(() {
      _dash = results[0] as Map<String, dynamic>?;
      _care = results[1] as Map<String, dynamic>?;
      _lab = results[2] as List<dynamic>;
      _me = results[3] as Map<String, dynamic>?;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Espace Patient'),
        backgroundColor: const Color(0xFF0D9488),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
          IconButton(icon: const Icon(Icons.logout), onPressed: _logout),
        ],
      ),
      body: IndexedStack(
              index: _index,
              children: [
                _buildHomeTab(),
                const PatientAppointmentsTab(),
                _buildCareTab(),
                _buildLabTab(),
                const PatientPharmacyTab(),
                PatientBillingTab(key: ValueKey(_openPaymentOnBilling), autoOpenFirstUnpaid: _openPaymentOnBilling),
                const PatientCardTab(),
              ],
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() {
          _index = i;
          if (i != 5) _openPaymentOnBilling = false;
        }),
        labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: 'Accueil'),
          NavigationDestination(icon: Icon(Icons.calendar_today), label: 'RDV'),
          NavigationDestination(icon: Icon(Icons.healing), label: 'Soins'),
          NavigationDestination(icon: Icon(Icons.science), label: 'Labo'),
          NavigationDestination(icon: Icon(Icons.local_pharmacy), label: 'Pharma'),
          NavigationDestination(icon: Icon(Icons.payment), label: 'Payer'),
          NavigationDestination(icon: Icon(Icons.badge), label: 'Carte'),
        ],
      ),
    );
  }

  Widget _buildHomeTab() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final d = _dash ?? {};
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (_me != null)
          Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: const Color(0xFF0D9488),
                child: Text('${_me!['first_name']?[0] ?? 'P'}', style: const TextStyle(color: Colors.white)),
              ),
              title: Text('${_me!['first_name'] ?? ''} ${_me!['last_name'] ?? ''}'.trim()),
              subtitle: Text(_me!['email']?.toString() ?? ''),
            ),
          ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _statCard('RDV à venir', '${d['rdv_a_venir'] ?? 0}', Icons.calendar_today, Colors.teal),
            _statCard('Résultats labo', '${d['resultats_disponibles'] ?? 0}', Icons.science, Colors.blue),
            _statCard('Rappels', '${d['rappels_actifs'] ?? 0}', Icons.medication, Colors.purple),
            _statCard('Factures dues', '${d['factures_impayees'] ?? 0}', Icons.payment, Colors.red),
          ],
        ),
        if (parseInt(d['factures_impayees']) > 0) ...[
          const SizedBox(height: 12),
          Card(
            color: Colors.red.shade50,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Icon(Icons.payment, color: Colors.red.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${d['factures_impayees']} facture(s) — ${fmtMoney(d['montant_du'])} FCFA',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Paiement Mobile Money disponible dans l\'application (MTN / Airtel)',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: () => setState(() {
                      _openPaymentOnBilling = true;
                      _index = 5;
                    }),
                    icon: const Icon(Icons.phone_android),
                    label: Text('Payer ${fmtMoney(d['montant_du'])} FCFA'),
                  ),
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => setState(() => _index = 4),
          icon: const Icon(Icons.local_pharmacy),
          label: const Text('Commander à la pharmacie'),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => setState(() => _index = 6),
          icon: const Icon(Icons.badge),
          label: const Text('Ma carte patient PDF'),
        ),
        if (d['hospitalisation_active'] == true) ...[
          const SizedBox(height: 16),
          Card(
            color: Colors.amber.shade50,
            child: const ListTile(
              leading: Icon(Icons.local_hospital, color: Colors.amber),
              title: Text('Hospitalisation en cours'),
              subtitle: Text('Consultez l\'onglet Soins pour le détail'),
            ),
          ),
        ],
        if (d['prochain_rdv'] != null) ...[
          const SizedBox(height: 16),
          Text('Prochain RDV', style: Theme.of(context).textTheme.titleMedium),
          Card(
            child: ListTile(
              title: Text(d['prochain_rdv']['medecin']?.toString() ?? 'Médecin'),
              subtitle: Text('${_fmtDate(d['prochain_rdv']['date_heure'])} — ${d['prochain_rdv']['motif'] ?? ''}'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _statCard(String label, String value, IconData icon, Color color) {
    return SizedBox(
      width: 160,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 22),
              const SizedBox(height: 8),
              Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCareTab() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final c = _care ?? {};
    final hosp = c['hospitalisation'] as Map<String, dynamic>?;
    final soins = c['soins'] as List? ?? [];
    final ordonnances = c['ordonnances'] as List? ?? [];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (hosp != null) ...[
          Card(
            color: Colors.amber.shade50,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Hospitalisation', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 6),
                  Text(hosp['localisation']?.toString() ?? ''),
                  Text('Médecin : ${hosp['medecin_referent'] ?? ''}', style: const TextStyle(fontSize: 13)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Text('Soins infirmiers (${soins.length})', style: Theme.of(context).textTheme.titleMedium),
        ...soins.map((s) => Card(
              child: ListTile(
                title: Text(s['description']?.toString() ?? ''),
                subtitle: Text('${_fmtDate(s['planifie_a'])} — ${s['statut_label'] ?? ''}'),
              ),
            )),
        if (soins.isEmpty && hosp == null)
          const Card(child: ListTile(title: Text('Pas de plan de soins actif'))),
        const SizedBox(height: 16),
        Text('Ordonnances (${ordonnances.length})', style: Theme.of(context).textTheme.titleMedium),
        ...ordonnances.map((o) => Card(
              child: ListTile(
                title: Text(o['medicament']?.toString() ?? ''),
                subtitle: Text('${o['posologie'] ?? ''} — ${o['medecin'] ?? ''}'),
              ),
            )),
      ],
    );
  }

  Widget _buildLabTab() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Résultats laboratoire', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (_lab.isEmpty) const Card(child: ListTile(title: Text('Aucun résultat publié'))),
        ..._lab.map((r) => Card(
              child: ListTile(
                title: Text(r['examen']?.toString() ?? ''),
                subtitle: Text('${r['valeur'] ?? ''} ${r['unite'] ?? ''}'),
                trailing: r['pdf_url'] != null && r['pdf_url'].toString().isNotEmpty
                    ? const Icon(Icons.picture_as_pdf, color: Colors.red)
                    : null,
              ),
            )),
      ],
    );
  }
}
