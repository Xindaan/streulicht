"""Ist die ausgelieferte Seite frisch?  Der Waechter AUSSERHALB des Macs.

T-0075 (Review alarm#5, betrieb#3): Faellt der Mac aus (zugeklappt, ohne
Netz, aus), faellt jeder Waechter auf dem Mac mit aus, und `last exit code`
der Agenten wird vom naechsten Leerlauf-Tick mit 0 ueberschrieben.  Dieses
Skript laeuft deshalb auf GitHub (.github/workflows/waechter.yml): es liest
den Abrufzeitpunkt, den seite.py als
<meta name="streulicht-geholt" content="ISO-UTC"> in die Seite schreibt,
und endet mit Exitcode 1, wenn er fehlt oder aelter als die Grenze ist.
GitHub schickt bei einem fehlgeschlagenen geplanten Lauf eine Mail.

Nur Standardbibliothek; liest eine schon geholte Datei, holt selbst nichts.

Lauf:  python3 skripte/waechter.py seite.html [--grenze-h 30]
"""
import argparse
import re
import sys
from datetime import datetime, timezone

GRENZE_H = 30

MUSTER = re.compile(
    r'<meta\s+name="streulicht-geholt"\s+content="([^"]*)"', re.I)


def geholt(html):
    """Abrufzeitpunkt aus der Seite (aware, UTC) oder None."""
    m = MUSTER.search(html)
    if not m:
        return None
    try:
        t = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


def urteil(html, jetzt, grenze_h=GRENZE_H):
    """(ok, Text).  ok ist False, wenn der Zeitpunkt fehlt oder zu alt ist."""
    t = geholt(html)
    if t is None:
        return False, "Kein Abrufzeitpunkt in der Seite (streulicht-geholt fehlt)"
    alter_h = (jetzt - t).total_seconds() / 3600.0
    if alter_h > grenze_h:
        return False, ("Seite veraltet: geholt %s UTC, vor %.1f h (Grenze %d h)"
                       % (t.strftime("%d.%m. %H:%M"), alter_h, grenze_h))
    return True, ("Seite frisch: geholt %s UTC, vor %.1f h"
                  % (t.strftime("%d.%m. %H:%M"), alter_h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datei")
    ap.add_argument("--grenze-h", type=float, default=GRENZE_H)
    a = ap.parse_args()
    with open(a.datei, encoding="utf-8", errors="replace") as f:
        html = f.read()
    ok, text = urteil(html, datetime.now(timezone.utc), a.grenze_h)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
