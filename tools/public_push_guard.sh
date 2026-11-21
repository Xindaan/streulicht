#!/usr/bin/env bash
#
# public_push_guard.sh -- fail-closed pre-push-Hook fuer dieses PUBLIC Repo.
#
# Installation: tools/install_push_guard.sh
#   (kopiert diese Datei nach .git/hooks/pre-push und die Marker-Quelle
#    .private/leak_markers.sh daneben, prueft beide Kopien per shasum)
#
# Die Marker liegen in .private/ (gitignoriert), weil sie genau die Werte
# enthalten, die nicht ins Repo duerfen. Fehlt die Marker-Quelle oder bricht
# eine Pruefung technisch ab, wird der Push VERWEIGERT. Kein --no-verify:
# der Schalter kippt ALLE Pruefungen, nicht die eine, die meldet.
#
# Geprueft wird JEDER Commit im Push-Bereich (Inhalt, Dateinamen, Message,
# Autor), nicht nur die Spitze: ein Marker, der in Commit A auftaucht und in
# B verschwindet, landet trotzdem im Objectstore des Remotes.

set -uo pipefail

HOOKDIR="$(cd "$(dirname "$0")" && pwd)"
MARKER="$HOOKDIR/leak_markers.sh"

rot()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }
gruen(){ printf '\033[32m%s\033[0m\n' "$*" >&2; }

# Technischer Abbruch einer Pruefung = Push verweigern (T-0091). Ein leerer
# Treffertext heisst nur dann "sauber", wenn das Werkzeug mit 0 oder 1
# geendet hat; grep/git grep melden Fehler mit >= 2 (ungueltiges Muster: 2
# bzw. 128). Darum nie `2>/dev/null | head || true`.
technisch() {
  rot "PUSH VERWEIGERT: Pruefung technisch gescheitert ($1, Exitcode $2)."
  rot "  -> Marker-Quelle bzw. Muster pruefen; kein --no-verify."
  exit 1
}
# Exitcode einer Suche bewerten: 0 = Treffer, 1 = keiner, sonst Abbruch.
suche_ok() { [ "$2" -le 1 ] || technisch "$1" "$2"; }

if [ ! -r "$MARKER" ]; then
  rot "PUSH VERWEIGERT: Marker-Quelle fehlt ($MARKER)."
  rot "  -> tools/install_push_guard.sh"
  exit 1
fi
# shellcheck source=/dev/null
. "$MARKER"
if [ "${LM_MARKERS_GELADEN:-0}" != "1" ] || [ -z "${LM_HART_RE:-}" ]; then
  rot "PUSH VERWEIGERT: Marker-Quelle unvollstaendig geladen."
  exit 1
fi
# Pfade, in denen LM_BETRIEB_RE (Home-Pfad, launchd-Label) geduldet ist,
# solange die Betriebsbezeichner nicht umgestellt sind. Leer = nirgends.
LM_BETRIEB_PFADE="${LM_BETRIEB_PFADE:-}"

# --- Push-Bereich bestimmen -------------------------------------------------
NULL_OID="0000000000000000000000000000000000000000"
COMMITS=""
BASIS_UNBEKANNT=0
while read -r _lref loid _rref roid; do
  [ -z "${loid:-}" ] && continue
  [ "$loid" = "$NULL_OID" ] && continue          # Branch-Loeschung
  if [ -n "${roid:-}" ] && [ "$roid" != "$NULL_OID" ] \
     && git cat-file -e "${roid}^{commit}" 2>/dev/null; then
    neu="$(git rev-list "$roid..$loid")" || technisch "rev-list $roid..$loid" $?
  else
    # Remote-Stand lokal unbekannt (neuer Branch oder force-push nach
    # Rewrite): NICHT auf eine leere Range zurueckfallen, sondern alles
    # scannen, was der Push traegt -- abzueglich dessen, was der Remote
    # nachweislich schon hat.
    BASIS_UNBEKANNT=1
    neu="$(git rev-list "$loid" --not --remotes)" \
      || technisch "rev-list $loid --not --remotes" $?
    if [ -z "$neu" ]; then
      neu="$(git rev-list "$loid")" || technisch "rev-list $loid" $?
    fi
    echo "Public-Guard: Remote-Stand ${roid:-<neu>} unbekannt -- scanne ab $loid ohne bekannte Remote-Commits" >&2
  fi
  COMMITS="$COMMITS $neu"
done

ANZ="$(printf '%s\n' $COMMITS | grep -c . || true)"
if [ "${ANZ:-0}" -eq 0 ]; then
  if [ "$BASIS_UNBEKANNT" -eq 1 ]; then
    rot "PUSH VERWEIGERT: Push-Bereich nicht bestimmbar (0 Commits aufgeloest)."
    exit 1
  fi
  gruen "Public-Guard: keine neuen Commits im Push-Bereich."
  exit 0
fi
for c in $COMMITS; do
  git cat-file -e "${c}^{commit}" 2>/dev/null || {
    rot "PUSH VERWEIGERT: Commit $c nicht auffindbar -- Scan waere leer."
    exit 1
  }
done
echo "Public-Guard: $ANZ Commit(s) im Push-Bereich" >&2

fehler=0
melde() { rot "  [$1] $2"; fehler=$((fehler + 1)); }
eintraege=0

for c in $COMMITS; do
  kurz="$(git log -1 --format=%h "$c")" || technisch "log $c" $?
  baum="$(git ls-tree -r --name-only "$c")" || technisch "ls-tree $c" $?
  n="$(printf '%s\n' "$baum" | grep -c .)"
  eintraege=$((eintraege + n))

  # 1) harte Marker im Inhalt (alle Textdateien; git grep ueberspringt Binaeres)
  tr="$(git grep -nIE "$LM_HART_RE" "$c" -- .)"; rc=$?
  suche_ok "git grep LM_HART_RE" "$rc"
  if [ -n "$tr" ]; then
    melde "$kurz" "harte Marker im Inhalt:"
    printf '%s\n' "$tr" | head -25 | sed 's/^/      /' >&2
  fi

  # 2) Betriebsbezeichner (Home-Pfad, launchd-Label) ausserhalb der Duldung
  if [ -n "${LM_BETRIEB_RE:-}" ]; then
    roh="$(git grep -nIE "$LM_BETRIEB_RE" "$c" -- .)"; rc=$?
    suche_ok "git grep LM_BETRIEB_RE" "$rc"
    tr=""
    if [ -n "$roh" ]; then
      tr="$(printf '%s\n' "$roh" | sed "s/^$c://" \
            | grep -vE "^(${LM_BETRIEB_PFADE:-^\$}):")"; rc=$?
      suche_ok "grep -v LM_BETRIEB_PFADE" "$rc"
    fi
    if [ -n "$tr" ]; then
      melde "$kurz" "Betriebsbezeichner ausserhalb der geduldeten Pfade:"
      printf '%s\n' "$tr" | head -25 | sed 's/^/      /' >&2
    fi
  fi

  # 3) Dateinamen gegen die Verbotsliste
  if [ -n "${LM_PFAD_RE:-}" ]; then
    pf="$(printf '%s\n' "$baum" | grep -E "$LM_PFAD_RE")"; rc=$?
    suche_ok "grep LM_PFAD_RE" "$rc"
    if [ -n "$pf" ]; then
      melde "$kurz" "verbotener Pfad im Baum:"
      printf '%s\n' "$pf" | sed 's/^/      /' >&2
    fi
  fi

  # 4) Commit-Message und Autor-/Committer-Daten
  msg="$(git log -1 --format='%B%n%an %ae%n%cn %ce' "$c")" || technisch "log $c" $?
  mt="$(printf '%s\n' "$msg" | grep -nE "$LM_HART_RE")"; rc=$?
  suche_ok "grep LM_HART_RE (Message)" "$rc"
  if [ -n "$mt" ]; then
    melde "$kurz" "harte Marker in Message/Autor:"
    printf '%s\n' "$mt" | sed 's/^/      /' >&2
  fi

  # 5) neue Binaerdateien melden (nicht blocken)
  if git rev-parse -q --verify "${c}^" >/dev/null 2>&1; then
    neue="$(git diff-tree -r --diff-filter=A --name-only "${c}^" "$c")" \
      || technisch "diff-tree $c" $?
  else
    neue="$baum"
  fi
  bin="$(printf '%s\n' "$neue" | grep -iE '\.(png|jpe?g|gif|webp|heic|pdf|sqlite|db|zip|gz|xlsx?|pkl)$' || true)"
  [ -n "$bin" ] && { rot "  [$kurz] HINWEIS neue Binaerdateien (EXIF/Kartenausschnitte pruefen):"; printf '%s\n' "$bin" | sed 's/^/      /' >&2; }
done

echo "Public-Guard: $eintraege Baum-Eintraege ueber $ANZ Commit(s) geprueft" >&2
if [ "$fehler" -gt 0 ]; then
  rot "PUSH VERWEIGERT: $fehler Befund(e). KEIN --no-verify -- Befund beheben, Commit ersetzen."
  exit 1
fi
gruen "Public-Guard: sauber."
exit 0
