import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/format_utils.dart';

class DoctorPharmacyTab extends StatefulWidget {
  const DoctorPharmacyTab({super.key});

  @override
  State<DoctorPharmacyTab> createState() => _DoctorPharmacyTabState();
}

class _DoctorPharmacyTabState extends State<DoctorPharmacyTab> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _loading = true;
  List<dynamic> _medications = [];
  List<dynamic> _stocks = [];
  List<dynamic> _requests = [];
  final _search = TextEditingController();
  String _filterCat = '';
  String _filterStatut = '';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.staffMedications(),
      ApiService.staffPharmacyStocks(),
      ApiService.staffPharmacyRequests(statut: _filterStatut),
    ]);
    if (!mounted) return;
    setState(() {
      _medications = results[0];
      _stocks = results[1];
      _requests = results[2];
      _loading = false;
    });
  }

  List<dynamic> get _filteredMeds {
    final q = _search.text.trim().toLowerCase();
    return _medications.where((m) {
      if (_filterCat.isNotEmpty && m['categorie'] != _filterCat) return false;
      if (q.isEmpty) return true;
      final nom = (m['nom'] ?? '').toString().toLowerCase();
      final code = (m['code'] ?? '').toString().toLowerCase();
      return nom.contains(q) || code.contains(q);
    }).toList();
  }

  List<String> get _categories =>
      _medications.map((m) => m['categorie']?.toString() ?? '').where((c) => c.isNotEmpty).toSet().toList()
        ..sort();

  Color _statutColor(String? s) {
    switch (s) {
      case 'PRETE':
        return Colors.green;
      case 'EN_PREPARATION':
        return Colors.orange;
      case 'ANNULEE':
        return Colors.red;
      default:
        return Colors.blue;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    final soumises = _requests.where((r) => r['statut'] == 'SOUMISE').length;
    final ruptures = _stocks.where((s) => s['alerte'] == true).length;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Row(
            children: [
              _miniStat('Produits', '${_medications.length}', Icons.medication),
              const SizedBox(width: 8),
              _miniStat('Demandes', '$soumises', Icons.shopping_cart),
              const SizedBox(width: 8),
              _miniStat('Alertes', '$ruptures', Icons.warning_amber, color: Colors.orange),
            ],
          ),
        ),
        Material(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          child: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: 'Catalogue'),
              Tab(text: 'Stocks'),
              Tab(text: 'Demandes'),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [_buildCatalogue(), _buildStocks(), _buildRequests()],
          ),
        ),
      ],
    );
  }

  Widget _miniStat(String label, String value, IconData icon, {Color? color}) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          child: Row(
            children: [
              Icon(icon, size: 18, color: color ?? const Color(0xFF1E40AF)),
              const SizedBox(width: 6),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCatalogue() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _search,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Rechercher…',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Toutes'),
                  selected: _filterCat.isEmpty,
                  onSelected: (_) => setState(() => _filterCat = ''),
                ),
                ..._categories.map((c) => Padding(
                      padding: const EdgeInsets.only(left: 6),
                      child: FilterChip(
                        label: Text(c),
                        selected: _filterCat == c,
                        onSelected: (_) => setState(() => _filterCat = c),
                      ),
                    )),
              ],
            ),
          ),
          const SizedBox(height: 12),
          ..._filteredMeds.map((m) {
            final med = m as Map<String, dynamic>;
            return Card(
              child: ListTile(
                title: Text(med['nom']?.toString() ?? ''),
                subtitle: Text(
                  '${med['forme'] ?? ''} • ${fmtMoney(med['prix_unitaire'])} FCFA\n'
                  'Stock : ${med['stock_disponible'] ?? 0}',
                  style: const TextStyle(fontSize: 12),
                ),
                isThreeLine: true,
                trailing: med['disponible'] == true
                    ? const Icon(Icons.check_circle, color: Colors.green)
                    : const Icon(Icons.cancel, color: Colors.red),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildStocks() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Card(
            color: Color(0xFFE3F2FD),
            child: Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'Consultation des stocks — lecture seule. La gestion des lots est réservée au pharmacien.',
                style: TextStyle(fontSize: 13),
              ),
            ),
          ),
          const SizedBox(height: 8),
          ..._stocks.map((s) {
            final lot = s as Map<String, dynamic>;
            final alerte = lot['alerte'] == true;
            return Card(
              color: alerte ? Colors.orange.shade50 : null,
              child: ListTile(
                leading: Icon(alerte ? Icons.warning : Icons.inventory_2, color: alerte ? Colors.orange : null),
                title: Text(lot['medicament']?.toString() ?? ''),
                subtitle: Text(
                  'Lot ${lot['lot'] ?? '—'} • Qté ${lot['quantite'] ?? 0}\n'
                  'Péremption : ${lot['peremption'] ?? '—'}',
                  style: const TextStyle(fontSize: 12),
                ),
                isThreeLine: true,
                trailing: Text('${fmtMoney(lot['prix_unitaire'])} F', style: const TextStyle(fontSize: 11)),
              ),
            );
          }),
          if (_stocks.isEmpty) const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Aucun lot en stock'))),
        ],
      ),
    );
  }

  Widget _buildRequests() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<String>(
            value: _filterStatut.isEmpty ? '' : _filterStatut,
            decoration: const InputDecoration(labelText: 'Filtrer par statut', border: OutlineInputBorder(), isDense: true),
            items: const [
              DropdownMenuItem(value: '', child: Text('Tous')),
              DropdownMenuItem(value: 'SOUMISE', child: Text('Soumise')),
              DropdownMenuItem(value: 'EN_PREPARATION', child: Text('En préparation')),
              DropdownMenuItem(value: 'PRETE', child: Text('Prête')),
              DropdownMenuItem(value: 'RETIREE', child: Text('Retirée')),
            ],
            onChanged: (v) {
              setState(() => _filterStatut = v ?? '');
              _load();
            },
          ),
          const SizedBox(height: 12),
          ..._requests.map((r) {
            final req = r as Map<String, dynamic>;
            final lignes = req['lignes'] as List? ?? [];
            return Card(
              child: ExpansionTile(
                leading: Icon(Icons.receipt_long, color: _statutColor(req['statut']?.toString())),
                title: Text(req['reference']?.toString() ?? ''),
                subtitle: Text(
                  '${req['patient_nom'] ?? 'Patient'} • Dossier ${req['patient_dossier'] ?? '—'}\n'
                  '${req['statut_label'] ?? req['statut']} • ${fmtMoney(req['montant_total'])} FCFA',
                  style: const TextStyle(fontSize: 12),
                ),
                children: lignes.map((l) {
                  final line = l as Map<String, dynamic>;
                  return ListTile(
                    dense: true,
                    title: Text(line['medicament_nom']?.toString() ?? ''),
                    trailing: Text('×${line['quantite']}'),
                  );
                }).toList(),
              ),
            );
          }),
          if (_requests.isEmpty) const Card(child: ListTile(title: Text('Aucune demande patient'))),
        ],
      ),
    );
  }
}
