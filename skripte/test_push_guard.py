"""Pre-push-Guard des public Repos gegen einen Wegwerf-Remote (T-0091).

Der Guard (`tools/public_push_guard.sh`) muss fail-closed sein: scheitert eine
Pruefung technisch (ungueltiges Muster, git-Fehler), wird der Push verweigert.
Vorher schluckte `2>/dev/null | head -25 || true` den Exitcode 128 von
`git grep` mit ungueltigem Muster, der Treffertext war leer und der Guard
meldete "sauber".

Jeder Fall baut ein frisches Repo mit einem nackten Remote, installiert den
Guard samt einer erfundenen Marker-Quelle als pre-push-Hook und pusht
wirklich. Gemessen wird das ERGEBNIS: Exitcode von `git push` und ob der
Commit danach im Remote liegt. Kein Netz, kein echtes Repo, keine echten
Marker.

Lauf:  .venv/bin/python3 skripte/test_push_guard.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

_hier = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(os.path.dirname(_hier), "tools", "public_push_guard.sh")

fehler = 0


def pruefe(bed, text):
    global fehler
    print("   %s  %s" % ("ok  " if bed else "FEHL", text))
    if not bed:
        fehler += 1


def git(cwd, *args, pruefen=True):
    umg = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM="1", LC_ALL="C")
    r = subprocess.run(["git", "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", *args],
                       cwd=cwd, env=umg, capture_output=True, text=True,
                       timeout=60)
    if pruefen and r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr))
    return r


def push_mit(marker, inhalt="harmloser Text\n", vorpush=True):
    """Pusht einen Commit durch den Guard; liefert (rc, stderr, im_remote)."""
    d = tempfile.mkdtemp(prefix="guardtest_")
    try:
        fern = os.path.join(d, "fern.git")
        arbeit = os.path.join(d, "arbeit")
        git(d, "init", "-q", "--bare", fern)
        git(d, "init", "-q", "-b", "main", arbeit)
        with open(os.path.join(arbeit, "a.txt"), "w") as f:
            f.write("Basis\n")
        git(arbeit, "add", "a.txt")
        git(arbeit, "commit", "-q", "-m", "Basis")
        git(arbeit, "remote", "add", "origin", fern)
        if vorpush:
            # Basis ohne Hook pushen: der eigentliche Push hat dann einen
            # bekannten Remote-Stand (Pfad ueber rev-list roid..loid).
            git(arbeit, "push", "-q", "origin", "main")
        hooks = os.path.join(arbeit, ".git", "hooks")
        shutil.copy(GUARD, os.path.join(hooks, "pre-push"))
        os.chmod(os.path.join(hooks, "pre-push"), 0o755)
        if marker is not None:
            with open(os.path.join(hooks, "leak_markers.sh"), "w") as f:
                f.write(marker)
        with open(os.path.join(arbeit, "b.txt"), "w") as f:
            f.write(inhalt)
        git(arbeit, "add", "b.txt")
        git(arbeit, "commit", "-q", "-m", "Aenderung")
        spitze = git(arbeit, "rev-parse", "HEAD").stdout.strip()
        r = git(arbeit, "push", "origin", "main", pruefen=False)
        drin = git(fern, "cat-file", "-e", spitze + "^{commit}",
                   pruefen=False).returncode == 0
        return r.returncode, r.stderr, drin
    finally:
        shutil.rmtree(d, ignore_errors=True)


def marker(hart="GEHEIMWORT", betrieb=None, pfade=None, pfad=None):
    zeilen = ["LM_MARKERS_GELADEN=1", "LM_HART_RE='%s'" % hart]
    if betrieb is not None:
        zeilen.append("LM_BETRIEB_RE='%s'" % betrieb)
    if pfade is not None:
        zeilen.append("LM_BETRIEB_PFADE='%s'" % pfade)
    if pfad is not None:
        zeilen.append("LM_PFAD_RE='%s'" % pfad)
    return "\n".join(zeilen) + "\n"


def faelle():
    print("Pre-push-Guard gegen Wegwerf-Remote")

    rc, err, drin = push_mit(marker(betrieb="BETRIEBSPFAD", pfade="c\\.txt",
                                    pfad="^verboten/"))
    pruefe(rc == 0 and drin and "sauber" in err,
           "sauberer Fall laeuft durch (rc=%d)" % rc)

    rc, err, drin = push_mit(marker(), inhalt="steht GEHEIMWORT drin\n")
    pruefe(rc != 0 and not drin and "harte Marker" in err,
           "echter Treffer im Inhalt wird verweigert (rc=%d)" % rc)

    # Der gemessene Fall aus T-0091: git grep endet mit 128.
    rc, err, drin = push_mit(marker(hart="("))
    pruefe(rc != 0 and not drin and "technisch" in err,
           "ungueltiges hartes Muster verweigert (rc=%d)" % rc)

    rc, err, drin = push_mit(marker(betrieb="("))
    pruefe(rc != 0 and not drin and "technisch" in err,
           "ungueltiges Betriebsmuster verweigert (rc=%d)" % rc)

    # Treffer nur in geduldetem Pfad: grep -v endet mit 1 und das ist sauber.
    rc, err, drin = push_mit(marker(betrieb="BETRIEBSPFAD", pfade="b\\.txt"),
                             inhalt="BETRIEBSPFAD\n")
    pruefe(rc == 0 and drin and "sauber" in err,
           "Treffer im geduldeten Pfad laeuft durch (rc=%d)" % rc)

    # Treffer fuer das Betriebsmuster, der Duldungsfilter (grep -v) scheitert.
    rc, err, drin = push_mit(marker(betrieb="BETRIEBSPFAD", pfade="("),
                             inhalt="BETRIEBSPFAD\n")
    pruefe(rc != 0 and not drin and "technisch" in err,
           "ungueltiges Duldungsmuster verweigert (rc=%d)" % rc)

    rc, err, drin = push_mit(marker(pfad="("))
    pruefe(rc != 0 and not drin and "technisch" in err,
           "ungueltiges Pfadmuster verweigert (rc=%d)" % rc)

    rc, err, drin = push_mit(None)
    pruefe(rc != 0 and not drin and "Marker-Quelle fehlt" in err,
           "fehlende Marker-Quelle verweigert (rc=%d)" % rc)

    # Neuer Branch ohne Remote-Stand: Bereich ueber --not --remotes.
    rc, err, drin = push_mit(marker(hart="("), vorpush=False)
    pruefe(rc != 0 and not drin and "technisch" in err,
           "ungueltiges Muster auch beim Erst-Push verweigert (rc=%d)" % rc)


if __name__ == "__main__":
    if not os.path.exists(GUARD):
        print("FEHL Guard fehlt: %s" % GUARD)
        sys.exit(1)
    faelle()
    if fehler:
        print("%d Fehler" % fehler)
        sys.exit(1)
    print("alle Pruefungen gruen")
