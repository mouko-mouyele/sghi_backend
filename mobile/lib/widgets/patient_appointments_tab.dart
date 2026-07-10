import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../utils/format_utils.dart';

class PatientAppointmentsTab extends StatefulWidget {
  const PatientAppointmentsTab({super.key});

  @override
  State<PatientAppointmentsTab> createState() => _PatientAppointmentsTabState();
}

class _PatientAppointmentsTabState extends State<PatientAppointmentsTab> {
  bool _loading = true;
  bool _submitting = false;
  bool _showForm = false;
  List<dynamic> _rdv = [];
  List<dynamic> _medecins = [];
  List<dynamic> _busySlots = [];
  int? _selectedMedecinId;
  DateTime? _selectedDateTime;
  final _motif = TextEditingController(text: 'Consultation');
  String? _message;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _motif.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    final results = await Future.wait([
      ApiService.patientAppointments(),
      ApiService.availableDoctors(),
    ]);
    if (!mounted) return;
    setState(() {
      _rdv = results[0];
      _medecins = results[1];
      _loading = false;
    });
  }

  Future<void> _loadBusySlots() async {
    if (_selectedMedecinId == null || _selectedDateTime == null) {
      setState(() => _busySlots = []);
      return;
    }
    final jour = formatDay(_selectedDateTime!);
    final slots = await ApiService.doctorBusySlots(_selectedMedecinId!, jour);
    if (mounted) setState(() => _busySlots = slots);
  }

  Future<void> _pickDateTime() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDateTime ?? now.add(const Duration(days: 1)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 90)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_selectedDateTime ?? date.add(const Duration(hours: 9))),
    );
    if (time == null) return;
    setState(() {
      _selectedDateTime = DateTime(date.year, date.month, date.day, time.hour, time.minute);
    });
    await _loadBusySlots();
  }

  Future<void> _book() async {
    if (_selectedMedecinId == null) {
      setState(() => _error = 'Choisissez un médecin');
      return;
    }
    if (_selectedDateTime == null) {
      setState(() => _error = 'Choisissez une date et une heure');
      return;
    }
    if (_selectedDateTime!.isBefore(DateTime.now())) {
      setState(() => _error = 'La date doit être dans le futur');
      return;
    }
    if (_motif.text.trim().isEmpty) {
      setState(() => _error = 'Indiquez un motif');
      return;
    }

    setState(() { _submitting = true; _error = null; _message = null; });
    final result = await ApiService.bookAppointment(
      medecinId: _selectedMedecinId!,
      dateHeure: formatLocalDateTime(_selectedDateTime!),
      motif: _motif.text.trim(),
    );
    if (!mounted) return;
    setState(() => _submitting = false);

    if (result.error != null) {
      setState(() => _error = result.error);
      return;
    }

    setState(() {
      _showForm = false;
      _message = 'Demande envoyée — en attente de confirmation par l\'accueil';
      _selectedMedecinId = null;
      _selectedDateTime = null;
      _busySlots = [];
    });
    await _load();
  }

  Future<void> _cancel(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Annuler le rendez-vous ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Non')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Oui, annuler')),
        ],
      ),
    );
    if (ok != true) return;
    final result = await ApiService.cancelAppointment(id);
    if (!mounted) return;
    if (result.error != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result.error!)));
      return;
    }
    setState(() => _message = 'Rendez-vous annulé');
    await _load();
  }

  Color _statutColor(String? s) {
    switch (s) {
      case 'CONFIRME':
        return Colors.green;
      case 'PLANIFIE':
        return Colors.orange;
      case 'ANNULE':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _statutLabel(String? s) {
    switch (s) {
      case 'PLANIFIE':
        return 'En attente';
      case 'CONFIRME':
        return 'Confirmé';
      case 'ANNULE':
        return 'Annulé';
      case 'TERMINE':
        return 'Terminé';
      default:
        return s ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Mes rendez-vous', style: Theme.of(context).textTheme.titleMedium),
              ),
              FilledButton.tonalIcon(
                onPressed: () => setState(() => _showForm = !_showForm),
                icon: Icon(_showForm ? Icons.close : Icons.add),
                label: Text(_showForm ? 'Fermer' : 'Prendre RDV'),
              ),
            ],
          ),
          if (_message != null) ...[
            const SizedBox(height: 8),
            Card(
              color: Colors.green.shade50,
              child: ListTile(dense: true, leading: const Icon(Icons.check_circle, color: Colors.green), title: Text(_message!)),
            ),
          ],
          if (_showForm) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Nouveau rendez-vous', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      value: _selectedMedecinId,
                      decoration: const InputDecoration(labelText: 'Médecin', border: OutlineInputBorder()),
                      items: _medecins.map((m) {
                        final med = m as Map<String, dynamic>;
                        return DropdownMenuItem(
                          value: med['id'] as int,
                          child: Text(
                            'Dr ${med['first_name'] ?? ''} ${med['last_name'] ?? ''} — ${med['specialty'] ?? 'Généraliste'}',
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      }).toList(),
                      onChanged: (v) {
                        setState(() => _selectedMedecinId = v);
                        _loadBusySlots();
                      },
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: _pickDateTime,
                      icon: const Icon(Icons.calendar_today),
                      label: Text(
                        _selectedDateTime == null
                            ? 'Choisir date et heure'
                            : fmtDateTime(formatLocalDateTime(_selectedDateTime!)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _motif,
                      decoration: const InputDecoration(labelText: 'Motif', border: OutlineInputBorder()),
                    ),
                    if (_busySlots.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.amber.shade50,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Créneaux déjà pris ce jour :', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                            ..._busySlots.map((s) {
                              final slot = s as Map<String, dynamic>;
                              return Text(
                                '• ${fmtDateTime(slot['debut']).split(' ').last} – ${fmtDateTime(slot['fin']).split(' ').last}',
                                style: const TextStyle(fontSize: 12),
                              );
                            }),
                          ],
                        ),
                      ),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 8),
                      Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
                    ],
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: _submitting ? null : _book,
                      child: _submitting
                          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Text('Confirmer la demande'),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 12),
          if (_rdv.isEmpty && !_showForm) const Card(child: ListTile(title: Text('Aucun rendez-vous'))),
          ..._rdv.map((r) {
            final rdv = r as Map<String, dynamic>;
            final statut = rdv['statut']?.toString();
            final canCancel = statut == 'PLANIFIE' || statut == 'CONFIRME';
            return Card(
              child: ListTile(
                leading: CircleAvatar(backgroundColor: _statutColor(statut), child: const Icon(Icons.event, color: Colors.white, size: 18)),
                title: Text(rdv['medecin_nom']?.toString() ?? rdv['motif']?.toString() ?? 'Consultation'),
                subtitle: Text(
                  '${rdv['medecin_specialty'] ?? ''}\n${fmtDateTime(rdv['date_heure'])} · ${rdv['motif'] ?? ''}\n${_statutLabel(statut)}',
                  style: const TextStyle(fontSize: 12),
                ),
                isThreeLine: true,
                trailing: canCancel
                    ? IconButton(
                        icon: const Icon(Icons.cancel_outlined, color: Colors.red),
                        onPressed: () => _cancel(rdv['id'] as int),
                      )
                    : null,
              ),
            );
          }),
        ],
      ),
    );
  }
}
