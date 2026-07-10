import 'package:flutter/services.dart';

/// Filtres de saisie alignés sur le portail web SGHL.
class SghlInputFilters {
  static final lettersOnly = FilteringTextInputFormatter.allow(
    RegExp(r"[a-zA-ZÀ-ÿ\s'\-]"),
  );

  static final phoneOnly = FilteringTextInputFormatter.allow(
    RegExp(r'[\d+\s\-]'),
  );

  static final digitsOnly = FilteringTextInputFormatter.digitsOnly;

  static final alnumOnly = FilteringTextInputFormatter.allow(
    RegExp(r'[a-zA-Z0-9_\-.]'),
  );

  static final textOnly = FilteringTextInputFormatter.allow(
    RegExp(r'[a-zA-ZÀ-ÿ0-9 .,;:()\-/\\#@&°]'),
  );
}

/// Numéro d'urgences officiel de l'établissement.
const hospitalEmergencyPhone = '+242 066967236';
