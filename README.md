# Alex Reviewit – Fernwartung (Agent)

Eigenes Fernwartungs-Programm (wie TeamViewer QuickSupport + Vollversion / AnyDesk)
für das Intranet **intranet.alexreviewit.at**.

- **Schnellhilfe (QuickSupport):** `remote-agent/schnellhilfe.py` → zeigt einen 6-stelligen Code.
- **Vollversion (Host):** `remote-agent/vollversion.py` → dauerhaft, mit ID + Zugriffs-Passwort.

## Fertige Programme bauen
Automatisch in der GitHub-Cloud: **Actions → „Build Fernwartung“ → Run workflow**.
Ergebnisse unter dem Lauf bei **Artifacts** (Windows `.exe`, macOS `.pkg`).
Ein Tag `fernwartung-v1` erzeugt zusätzlich ein **Release** mit allen vier Dateien.

Lokal: `remote-agent/BUILD-Windows.cmd` bzw. `BUILD-Mac.command`.
Details: `remote-agent/BAUEN-LIES-MICH.txt`.
