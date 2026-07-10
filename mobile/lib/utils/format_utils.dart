String fmtMoney(dynamic n) {
  final v = parseNum(n);
  final s = v.toStringAsFixed(0);
  final buf = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
    buf.write(s[i]);
  }
  return buf.toString();
}

/// Montant API Django (Decimal sérialisé en String ou num).
double parseNum(dynamic v, [double fallback = 0]) {
  if (v == null) return fallback;
  if (v is num) return v.toDouble();
  final s = v.toString().trim().replaceAll(' ', '').replaceAll(',', '.');
  return double.tryParse(s) ?? fallback;
}

int parseInt(dynamic v, [int fallback = 0]) {
  if (v == null) return fallback;
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse(v.toString().trim()) ?? fallback;
}

String fmtDateTime(dynamic iso) {
  if (iso == null) return '—';
  try {
    return DateTime.parse(iso.toString())
        .toLocal()
        .toString()
        .substring(0, 16)
        .replaceFirst('T', ' ');
  } catch (_) {
    return iso.toString();
  }
}

/// Format local sans fuseau pour l'API Django (comme datetime-local web).
String formatLocalDateTime(DateTime dt) {
  String p2(int n) => n.toString().padLeft(2, '0');
  return '${dt.year}-${p2(dt.month)}-${p2(dt.day)}T${p2(dt.hour)}:${p2(dt.minute)}:00';
}

String formatDay(DateTime dt) {
  String p2(int n) => n.toString().padLeft(2, '0');
  return '${dt.year}-${p2(dt.month)}-${p2(dt.day)}';
}

Map<String, String>? detectOperateur(String raw) {
  var digits = raw.replaceAll(RegExp(r'\D'), '');
  if (digits.startsWith('242')) digits = digits.substring(3);
  if (digits.length == 8) digits = '0$digits';
  if (!digits.startsWith('0') && digits.isNotEmpty) digits = '0$digits';
  if (digits.startsWith('06')) {
    return {'code': 'MTN', 'label': 'MTN MoMo', 'ussd': '*133*1#'};
  }
  if (digits.startsWith('04') || digits.startsWith('05')) {
    return {'code': 'AIRTEL', 'label': 'Airtel Money', 'ussd': '*128*1#'};
  }
  return null;
}
