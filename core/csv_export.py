"""Export CSV compatible Microsoft Excel (locale FR)."""

import csv
import io
from typing import Iterable, Sequence


def excel_csv_response(rows: Iterable[Sequence], headers: Sequence[str]) -> bytes:
    """
    Génère un CSV UTF-8 avec BOM et séparateur point-virgule
    pour ouverture directe dans Excel (Windows FR).
    """
    buffer = io.StringIO()
    buffer.write('\ufeff')
    writer = csv.writer(buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode('utf-8')
