import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/format_utils.dart';

class PatientPharmacyTab extends StatefulWidget {
  const PatientPharmacyTab({super.key});

  @override
  State<PatientPharmacyTab> createState() => _PatientPharmacyTabState();
}

class _PatientPharmacyTabState extends State<PatientPharmacyTab> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _loading = true;
  List<dynamic> _medications = [];
  List<dynamic> _requests = [];
  final Map<int, int> _cart = {};
  final _search = TextEditingController();
  String _filterCat = '';
  final _notes = TextEditingController();
  bool _submitting = false;

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
    _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.pharmacyCatalog(),
      ApiService.pharmacyRequests(),
    ]);
    if (!mounted) return;
    setState(() {
      _medications = results[0];
      _requests = results[1];
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

  List<Map<String, dynamic>> get _cartItems {
    return _cart.entries
        .where((e) => e.value > 0)
        .map((e) {
          final med = _medications.cast<Map<String, dynamic>?>().firstWhere(
                (m) => m!['id'] == e.key,
                orElse: () => null,
              );
          if (med == null) return null;
          return {...med, 'qty': e.value};
        })
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  double get _cartTotal =>
      _cartItems.fold(0, (s, i) => s + (i['prix_unitaire'] as num) * (i['qty'] as int));

  int get _cartCount => _cart.values.fold(0, (a, b) => a + b);

  List<String> get _categories =>
      _medications.map((m) => m['categorie']?.toString() ?? '').where((c) => c.isNotEmpty).toSet().toList()
        ..sort();

  void _addToCart(Map<String, dynamic> med) {
    if (med['disponible'] != true) return;
    final id = med['id'] as int;
    final stock = (med['stock_disponible'] as num?)?.toInt() ?? 0;
    final current = _cart[id] ?? 0;
    if (current >= stock) {
      _snack('Stock limité : $stock disponible(s)', error: true);
      return;
    }
    setState(() => _cart[id] = current + 1);
  }

  void _setQty(Map<String, dynamic> med, int qty) {
    final id = med['id'] as int;
    final stock = (med['stock_disponible'] as num?)?.toInt() ?? 0;
    final n = qty.clamp(0, stock);
    setState(() {
      if (n == 0) {
        _cart.remove(id);
      } else {
        _cart[id] = n;
      }
    });
  }

  Future<void> _submit() async {
    if (_cartItems.isEmpty) return;
    setState(() => _submitting = true);
    final lignes = _cartItems
        .map((i) => {'medicament_id': i['id'], 'quantite': i['qty']})
        .toList();
    final result = await ApiService.submitPharmacyRequest(
      lignes: lignes,
      notes: _notes.text.trim(),
    );
    if (!mounted) return;
    setState(() => _submitting = false);
    if (result.error != null) {
      _snack(result.error!, error: true);
      return;
    }
    setState(() {
      _cart.clear();
      _notes.clear();
    });
    _snack('Demande ${result.data!['reference']} envoyée');
    await _load();
    _tabController.animateTo(2);
  }

  void _snack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: error ? Colors.red.shade700 : null),
    );
  }

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

    return Column(
      children: [
        Material(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          child: TabBar(
            controller: _tabController,
            tabs: [
              const Tab(text: 'Catalogue'),
              Tab(text: 'Panier${_cartCount > 0 ? ' ($_cartCount)' : ''}'),
              const Tab(text: 'Demandes'),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [_buildCatalogue(), _buildCart(), _buildRequests()],
          ),
        ),
      ],
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
              hintText: 'Rechercher un médicament…',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Toutes'),
                  selected: _filterCat.isEmpty,
                  onSelected: (_) => setState(() => _filterCat = ''),
                ),
                ..._categories.map((c) {
                  final label = _medications
                          .cast<Map<String, dynamic>>()
                          .firstWhere((m) => m['categorie'] == c, orElse: () => {})['categorie_label']
                          ?.toString() ??
                      c;
                  return Padding(
                    padding: const EdgeInsets.only(left: 6),
                    child: FilterChip(
                      label: Text(label),
                      selected: _filterCat == c,
                      onSelected: (_) => setState(() => _filterCat = c),
                    ),
                  );
                }),
              ],
            ),
          ),
          const SizedBox(height: 12),
          const Card(
            color: Color(0xFFE0F2F1),
            child: Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'Retrait à la pharmacie du CHU. Le paiement se fait à la caisse après préparation.',
                style: TextStyle(fontSize: 13),
              ),
            ),
          ),
          const SizedBox(height: 8),
          ..._filteredMeds.map((m) {
            final med = m as Map<String, dynamic>;
            final dispo = med['disponible'] == true;
            final qty = _cart[med['id'] as int] ?? 0;
            return Card(
              child: ListTile(
                title: Text(med['nom']?.toString() ?? ''),
                subtitle: Text(
                  '${med['forme'] ?? ''} • ${fmtMoney(med['prix_unitaire'])} FCFA\n'
                  'Stock : ${med['stock_disponible'] ?? 0}',
                  style: const TextStyle(fontSize: 12),
                ),
                isThreeLine: true,
                trailing: dispo
                    ? (qty > 0
                        ? Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.remove_circle_outline),
                                onPressed: () => _setQty(med, qty - 1),
                              ),
                              Text('$qty'),
                              IconButton(
                                icon: const Icon(Icons.add_circle_outline),
                                onPressed: () => _addToCart(med),
                              ),
                            ],
                          )
                        : IconButton(
                            icon: const Icon(Icons.add_shopping_cart),
                            onPressed: () => _addToCart(med),
                          ))
                    : const Chip(label: Text('Rupture', style: TextStyle(fontSize: 11))),
              ),
            );
          }),
          if (_filteredMeds.isEmpty) const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Aucun médicament'))),
        ],
      ),
    );
  }

  Widget _buildCart() {
    final items = _cartItems;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (items.isEmpty)
          const Card(child: ListTile(title: Text('Panier vide'), subtitle: Text('Ajoutez des médicaments depuis le catalogue')))
        else ...[
          ...items.map((i) => Card(
                child: ListTile(
                  title: Text(i['nom']?.toString() ?? ''),
                  subtitle: Text('${fmtMoney(i['prix_unitaire'])} FCFA × ${i['qty']}'),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(icon: const Icon(Icons.remove), onPressed: () => _setQty(i, (i['qty'] as int) - 1)),
                      Text('${i['qty']}'),
                      IconButton(icon: const Icon(Icons.add), onPressed: () => _setQty(i, (i['qty'] as int) + 1)),
                    ],
                  ),
                ),
              )),
          const SizedBox(height: 8),
          Text('Total estimé : ${fmtMoney(_cartTotal)} FCFA', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            controller: _notes,
            decoration: const InputDecoration(
              labelText: 'Notes (optionnel)',
              border: OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _submitting ? null : _submit,
            icon: _submitting
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.send),
            label: Text(_submitting ? 'Envoi…' : 'Soumettre la demande'),
          ),
        ],
      ],
    );
  }

  Widget _buildRequests() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_requests.isEmpty) const Card(child: ListTile(title: Text('Aucune demande'))),
          ..._requests.map((r) {
            final req = r as Map<String, dynamic>;
            final lignes = req['lignes'] as List? ?? [];
            final statut = req['statut']?.toString();
            return Card(
              child: ExpansionTile(
                leading: Icon(Icons.receipt_long, color: _statutColor(statut)),
                title: Text(req['reference']?.toString() ?? ''),
                subtitle: Text(
                  '${req['statut_label'] ?? statut} • ${fmtDateTime(req['created_at'])}\n'
                  'Total : ${fmtMoney(req['montant_total'])} FCFA',
                ),
                children: lignes.map((l) {
                  final line = l as Map<String, dynamic>;
                  return ListTile(
                    dense: true,
                    title: Text(line['medicament_nom']?.toString() ?? ''),
                    trailing: Text('×${line['quantite']} — ${fmtMoney(line['sous_total'])} F'),
                  );
                }).toList(),
              ),
            );
          }),
        ],
      ),
    );
  }
}
