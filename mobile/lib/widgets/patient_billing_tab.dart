import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/format_utils.dart';

class MobileMoneySheet extends StatefulWidget {
  const MobileMoneySheet({
    super.key,
    required this.invoice,
    this.defaultPhone = '',
  });

  final Map<String, dynamic> invoice;
  final String defaultPhone;

  @override
  State<MobileMoneySheet> createState() => _MobileMoneySheetState();
}

class _MobileMoneySheetState extends State<MobileMoneySheet> {
  late final TextEditingController _phone;
  final _smsCode = TextEditingController();
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _tx;
  bool _done = false;
  Timer? _pollTimer;

  int get _invoiceId => parseInt(widget.invoice['id']);

  @override
  void initState() {
    super.initState();
    _phone = TextEditingController(text: _cleanPhone(widget.defaultPhone));
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _phone.dispose();
    _smsCode.dispose();
    super.dispose();
  }

  String _cleanPhone(String raw) {
    final digits = raw.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('242') && digits.length >= 11) {
      return '0${digits.substring(3, 11)}';
    }
    if (digits.length == 9 && digits.startsWith('0')) return digits;
    if (digits.length == 8) return '0$digits';
    return raw.trim();
  }

  void _stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  void _startPolling() {
    _stopPolling();
    final txId = _tx?['id'];
    if (txId == null) return;
    final txIdInt = parseInt(txId);
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      final status = await ApiService.mobileMoneyStatus(txIdInt);
      if (!mounted) return;
      if (status?['statut'] == 'CONFIRME') {
        _stopPolling();
        setState(() => _done = true);
      }
    });
  }

  Future<void> _startPayment() async {
    if (detectOperateur(_phone.text) == null) {
      setState(() => _error = 'Numéro MTN (06…) ou Airtel (04… / 05…) requis');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final result = await ApiService.initMobileMoney(_invoiceId, numeroMobile: _phone.text.trim());
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.error != null) {
      setState(() => _error = result.error);
      return;
    }
    final tx = result.data!;
    final code = tx['code_push']?.toString() ?? '';
    if (code.isNotEmpty) _smsCode.text = code;
    setState(() => _tx = tx);
    _startPolling();
  }

  Future<void> _approveOnPhone() async {
    final txId = _tx?['id'];
    if (txId == null) return;
    final txIdInt = parseInt(txId);
    setState(() { _loading = true; _error = null; });
    final result = await ApiService.approveMobileMoney(txIdInt, numeroMobile: _phone.text.trim());
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.error != null) {
      setState(() => _error = result.error);
      return;
    }
    _stopPolling();
    setState(() => _done = true);
  }

  Future<void> _confirmSms() async {
    if (_smsCode.text.trim().length < 4) {
      setState(() => _error = 'Entrez le code reçu sur votre téléphone');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final result = await ApiService.confirmMobileMoney(
      _invoiceId,
      transactionId: parseInt(_tx!['id']),
      codePush: _smsCode.text.trim(),
    );
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.error != null) {
      setState(() => _error = result.error);
      return;
    }
    _stopPolling();
    setState(() => _done = true);
  }

  @override
  Widget build(BuildContext context) {
    final op = detectOperateur(_phone.text);
    final montant = parseNum(widget.invoice['montant_restant']);

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('Paiement Mobile Money', style: Theme.of(context).textTheme.titleMedium),
                ),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
              ],
            ),
            Text('Facture ${widget.invoice['numero'] ?? ''}', style: const TextStyle(fontSize: 13, color: Colors.grey)),
            const SizedBox(height: 4),
            Text('Montant : ${fmtMoney(montant)} FCFA', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 16),
            if (_done) ...[
              const Icon(Icons.check_circle, color: Colors.green, size: 56),
              const SizedBox(height: 8),
              const Text('Paiement confirmé !', textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Fermer')),
            ] else if (_tx == null) ...[
              const Card(
                color: Color(0xFFE8F5E9),
                child: Padding(
                  padding: EdgeInsets.all(12),
                  child: Text(
                    'Paiement sécurisé depuis l\'application — MTN MoMo (06…) ou Airtel Money (04… / 05…)',
                    style: TextStyle(fontSize: 13),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'Numéro Mobile Money',
                  hintText: '06 123 45 67',
                  border: OutlineInputBorder(),
                ),
                onChanged: (_) => setState(() => _error = null),
              ),
              if (op != null) ...[
                const SizedBox(height: 8),
                Chip(
                  avatar: const Icon(Icons.phone_android, size: 18),
                  label: Text('${op['label']} • USSD ${op['ussd']}'),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loading ? null : _startPayment,
                icon: _loading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.phone_android),
                label: Text('Payer ${fmtMoney(montant)} FCFA'),
              ),
            ] else ...[
              Card(
                color: Colors.amber.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_tx!['push_message']?.toString() ?? 'Notification envoyée sur votre téléphone'),
                      if (_tx!['code_push'] != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text('Code : ${_tx!['code_push']}', style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _smsCode,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Code SMS / PIN', border: OutlineInputBorder()),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _loading ? null : _confirmSms,
                child: _loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('Valider le paiement'),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _loading ? null : _approveOnPhone,
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('J\'ai approuvé sur mon téléphone'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Onglet facturation patient — paiement Mobile Money intégré.
class PatientBillingTab extends StatefulWidget {
  const PatientBillingTab({super.key, this.autoOpenFirstUnpaid = false});

  /// Ouvre automatiquement le paiement de la 1re facture impayée (depuis l'accueil).
  final bool autoOpenFirstUnpaid;

  @override
  State<PatientBillingTab> createState() => _PatientBillingTabState();
}

class _PatientBillingTabState extends State<PatientBillingTab> {
  bool _loading = true;
  List<dynamic> _invoices = [];
  String? _defaultPhone;
  bool _autoOpened = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.patientInvoices(),
      ApiService.patientProfile(),
    ]);
    if (!mounted) return;
    setState(() {
      _invoices = results[0] as List<dynamic>;
      final profile = results[1] as Map<String, dynamic>?;
      _defaultPhone = profile?['telephone']?.toString();
      _loading = false;
    });
    if (widget.autoOpenFirstUnpaid && !_autoOpened) {
      _autoOpened = true;
      final first = _unpaidInvoices.firstOrNull;
      if (first != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _payInvoice(first));
      }
    }
  }

  List<Map<String, dynamic>> get _unpaidInvoices =>
      _invoices.where((i) => _isPayable(i as Map<String, dynamic>)).cast<Map<String, dynamic>>().toList();

  List<Map<String, dynamic>> get _paidInvoices =>
      _invoices.where((i) => (i as Map<String, dynamic>)['est_payee'] == true).cast<Map<String, dynamic>>().toList();

  bool _isPayable(Map<String, dynamic> invoice) {
    if (invoice['est_payee'] == true) return false;
    if (invoice['est_impayee'] == true) return true;
    final statut = invoice['statut']?.toString();
    final reste = parseNum(invoice['montant_restant']);
    return reste > 0 && (statut == 'EMISE' || statut == 'PARTIEL');
  }

  Future<void> _payInvoice(Map<String, dynamic> invoice) async {
    if (!_isPayable(invoice)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Facture ${invoice['numero']} non payable en ligne')),
        );
      }
      return;
    }

    final paid = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => MobileMoneySheet(
        invoice: invoice,
        defaultPhone: _defaultPhone ?? '061234567',
      ),
    );
    if (paid == true) {
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Paiement enregistré — facture mise à jour')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    final impayees = _unpaidInvoices;
    final totalDu = impayees.fold<double>(0, (s, i) => s + parseNum(i['montant_restant']));

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF047857), Color(0xFF0E7490)]),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Mes factures', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                const Text(
                  'Payez directement dans l\'application par MTN MoMo ou Airtel Money',
                  style: TextStyle(color: Colors.white70, fontSize: 13),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _headerStat('${impayees.length}', 'Impayée(s)'),
                    const SizedBox(width: 12),
                    _headerStat(fmtMoney(totalDu), 'FCFA dus'),
                    const SizedBox(width: 12),
                    _headerStat('${_paidInvoices.length}', 'Payée(s)'),
                  ],
                ),
              ],
            ),
          ),
          if (impayees.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('À payer maintenant', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...impayees.map((i) => _invoiceCard(i, highlightPay: true)),
          ],
          if (_paidInvoices.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('Historique — payées', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ..._paidInvoices.map((i) => _invoiceCard(i, highlightPay: false)),
          ],
          if (_invoices.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: Text('Aucune facture pour le moment')),
            ),
        ],
      ),
    );
  }

  Widget _headerStat(String value, String label) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
        child: Column(
          children: [
            Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 10)),
          ],
        ),
      ),
    );
  }

  Widget _invoiceCard(Map<String, dynamic> i, {required bool highlightPay}) {
    final reste = parseNum(i['montant_restant']);
    final lignes = i['lignes'] as List? ?? [];
    final payee = i['est_payee'] == true;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      color: payee ? null : Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(i['numero']?.toString() ?? '', style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Colors.teal)),
                      Text('${fmtMoney(i['montant_total'])} FCFA', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      Text(i['statut_libelle']?.toString() ?? '', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                ),
                Chip(
                  label: Text(payee ? 'Payée' : 'Impayée', style: const TextStyle(fontSize: 11)),
                  backgroundColor: payee ? Colors.green.shade100 : Colors.red.shade100,
                ),
              ],
            ),
            if (lignes.isNotEmpty) ...[
              const Divider(height: 20),
              ...lignes.take(3).map((l) {
                final line = l as Map<String, dynamic>;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(child: Text(line['libelle']?.toString() ?? '', style: const TextStyle(fontSize: 13))),
                      Text('${fmtMoney(line['montant'])} F', style: const TextStyle(fontSize: 13)),
                    ],
                  ),
                );
              }),
            ],
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Payé : ${fmtMoney(i['montant_paye'])} FCFA', style: const TextStyle(fontSize: 12)),
                if (!payee)
                  Text('Reste : ${fmtMoney(reste)} FCFA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.red.shade700)),
              ],
            ),
            if (highlightPay && _isPayable(i)) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () => _payInvoice(i),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFFF59E0B),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                icon: const Icon(Icons.phone_android),
                label: Text('Payer ${fmtMoney(reste)} FCFA — Mobile Money'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

extension _FirstOrNull<E> on Iterable<E> {
  E? get firstOrNull {
    final it = iterator;
    if (it.moveNext()) return it.current;
    return null;
  }
}
