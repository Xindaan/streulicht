#!/usr/bin/env bash
# install_push_guard.sh -- installiert den fail-closed pre-push-Guard in
# .git/hooks/ und prueft die Kopien per shasum. Nach jedem frischen Klon und
# nach jeder Aenderung an tools/public_push_guard.sh oder
# .private/leak_markers.sh laufen lassen (.git/hooks wird nicht versioniert).
set -euo pipefail
REPO="$(git rev-parse --show-toplevel)"
HOOKS="$(git rev-parse --git-path hooks)"
QUELLE_GUARD="$REPO/tools/public_push_guard.sh"
QUELLE_MARKER="$REPO/.private/leak_markers.sh"
[ -r "$QUELLE_MARKER" ] || { echo "FEHLT: $QUELLE_MARKER (lokal, gitignoriert) -- Guard bleibt ohne Muster und blockt jeden Push." >&2; exit 1; }
mkdir -p "$HOOKS"
cp "$QUELLE_GUARD"  "$HOOKS/pre-push"
cp "$QUELLE_MARKER" "$HOOKS/leak_markers.sh"
chmod +x "$HOOKS/pre-push"
for paar in "$QUELLE_GUARD:$HOOKS/pre-push" "$QUELLE_MARKER:$HOOKS/leak_markers.sh"; do
  a="$(shasum -a 256 "${paar%%:*}" | cut -d' ' -f1)"; b="$(shasum -a 256 "${paar#*:}" | cut -d' ' -f1)"
  [ "$a" = "$b" ] || { echo "shasum weicht ab: $paar" >&2; exit 1; }
done
# Marker muessen laden, sonst blockt der Hook jeden Push still mit Meldung.
( cd "$REPO" && . "$HOOKS/leak_markers.sh" && [ "${LM_MARKERS_GELADEN:-0}" = 1 ] ) \
  || { echo "Marker laden nicht vollstaendig (konfig_geheim.json?)" >&2; exit 1; }
echo "pre-push-Guard installiert und verifiziert: $HOOKS/pre-push"
