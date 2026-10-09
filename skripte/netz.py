"""Auf Netz warten, statt am ersten Fehlversuch zu sterben.

WARUM (17.08.2026).  Der Mac hatte an dem Morgen von 07:30 bis nach 08:15
keine Namensaufloesung - vermutlich WLAN nach dem Aufwachen.  Vier Agenten
liefen in dieses Fenster und starben alle vier mit demselben

    URLError: <urlopen error [Errno 8] nodename nor servname provided>

Jeder genau einmal, ohne Wiederholung.  Ergebnis: kein Alarmlauf, kein
Archiv, kein Bewertungsabruf, und die ausgelieferte Seite zeigte den ganzen
Tag den Vortag - ohne dass irgendwo etwas rot geworden waere.

launchd hilft hier nicht: `StartCalendarInterval` holt VERPASSTE Laeufe beim
Aufwachen nach, aber ein Lauf, der gestartet ist und fehlgeschlagen ist, gilt
als erledigt.  Also wartet das Skript selbst.

Bewusst nur DNS und bewusst nur Minuten: das ist kein Ersatz fuer einen
laufenden Rechner, sondern die Ueberbrueckung der zwei bis zehn Minuten
zwischen Aufwachen und Netz.
"""
import socket
import time

PROBE = "api.open-meteo.com"


def warte_auf_netz(minuten=20, pause=30, name=PROBE, melde=print):
    """True, sobald `name` aufloest; False, wenn die Frist ablaeuft.

    Der Rueckgabewert ist eine Information, keine Aufforderung: der Aufrufer
    entscheidet, ob er es trotzdem versucht.  Nichts hier bricht ab - ein
    Wartehelfer, der das Programm beendet, ist ein Wartehelfer, der bei der
    naechsten Aenderung uebersehen wird.
    """
    # WANDUHR, nicht monotonic (T-0070, 04.09.2026).  `time.monotonic()`
    # steht auf macOS waehrend des Ruhezustands still: schlaeft der Rechner
    # mitten im Warten ein, laeuft die Frist nicht weiter, und aus den
    # zugesagten 20 Minuten werden real Stunden.  Genau das ist am
    # 01.09.2026 passiert - "Warte bis zu 20 Minuten" um 18:28, "Netz ist
    # da" um 18:57.  Gemeint sind Minuten an der Wand, nicht Minuten wach.
    frist = time.time() + minuten * 60
    erster = True
    while True:
        try:
            socket.getaddrinfo(name, 443, proto=socket.IPPROTO_TCP)
            if not erster:
                melde("   Netz ist da.")
            return True
        except socket.gaierror:
            pass
        if time.time() >= frist:
            melde("   Kein Netz nach %d Minuten - es wird trotzdem versucht."
                  % minuten)
            return False
        if erster:
            melde("   Kein Netz. Warte bis zu %d Minuten ..." % minuten)
            erster = False
        time.sleep(pause)


if __name__ == "__main__":
    print("Netz erreichbar:", warte_auf_netz(minuten=1, pause=5))
