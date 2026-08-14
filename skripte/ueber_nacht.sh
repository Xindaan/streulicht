#!/bin/bash
# Grindet die Klimatologie durch, so weit das Kontingent jeweils traegt.
# klimatologie.py steigt bei Stunden-/Tageslimit sauber aus und cacht jeden
# Block; dieser Wrapper startet es einfach wieder. Laeuft unbeaufsichtigt.
cd "$(dirname "$0")/.." || exit 1
ZIEL="daten/score_berlin_g0.5_2015_2025.json"
for versuch in $(seq 1 40); do
  if [ -f "$ZIEL" ]; then
    echo "$(date -u +%H:%M) fertig nach $versuch Versuchen"; exit 0
  fi
  echo "=== $(date -u +%Y-%m-%dT%H:%M) Versuch $versuch"
  python3 skripte/klimatologie.py --von 2015 --bis 2025 2>&1 | tail -4
  [ -f "$ZIEL" ] && continue
  sleep 1800
done
echo "abgebrochen nach 40 Versuchen"
