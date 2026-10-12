# Änderungen

Die Versionen unter **Releases** sind fortlaufend nummeriert (1, 2, 3 …); jede
Änderung am Programm erzeugt automatisch eine neue. Diese Liste beschreibt, was
sich geändert hat – neueste zuerst.

## Oktober 2026

- **Ein‑Klick‑Update:** „Jetzt aktualisieren“ lädt den passenden Installer selbst
  herunter (mit Fortschritt), startet ihn und beendet das Programm. Zusätzlich
  „Später“ und „Nach Updates suchen“.
- **Fehler behoben:** Im Passwort‑Modus wurden Verbindungen am Gerät
  fälschlich abgelehnt – jetzt verbinden feste und Einmal‑Passwörter korrekt.
- **Stabiler Start:** Startfehler werden jetzt angezeigt und nach
  `~/Library/Logs/AlexReviewit-Fernwartung.log` (macOS) protokolliert, statt
  kommentarlos abzustürzen. Fehlende Bibliotheken (u. a. cryptography, cffi, mss)
  werden jetzt mitgebündelt.
- **Vollversion als Installer:** Windows‑Setup (Inno Setup) mit Programme‑Ordner,
  Startmenü‑Eintrag, optionalem Autostart und Uninstaller; macOS als `.pkg`.
- **Passwort‑Modell wie TeamViewer:** Wahl zwischen festem Passwort und
  automatischem Einmal‑Passwort pro Sitzung; bei der Einrichtung ist kein
  Passwort mehr nötig.
- **Zugriffsregeln am Gerät:** Fragen / Passwort / Automatisch / Gesperrt.
- **Numerische Geräte‑ID** (zum Kopieren) und **Verbinden per ID + Passwort** auf
  der Seite; eigene Geräte lassen sich löschen.
- **Fortlaufend nummerierte Releases** – alte Versionen bleiben erhalten.
- **Chat verbessert:** Zeitstempel, Absender, Ungelesen‑Zähler.
- **Design** der Programme an das Intranet angepasst (Verlaufs‑Kopfzeile,
  abgerundete Karten, klare Schrift).

> Diese Datei wird bei jeder Änderung am Fernwartungs‑Tool mitgepflegt.
