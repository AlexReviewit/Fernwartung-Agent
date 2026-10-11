#!/bin/bash
cd "$(dirname "$0")"
echo "============================================================"
echo "  Alex Reviewit - Fernwartung / Schnellhilfe"
echo "============================================================"
echo
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] Python 3 fehlt. Bitte von https://www.python.org/downloads/ installieren."
  read -n1 -s -r -p "Taste druecken ..."; exit 1
fi
echo "Installiere/aktualisiere Bausteine (nur beim ersten Mal) ..."
python3 -m pip install --disable-pip-version-check -q -r requirements.txt
echo
echo "Hinweis: Beim ersten Start fragt macOS nach Rechten fuer"
echo "Bildschirmaufnahme und Bedienungshilfen (Systemeinstellungen ->"
echo "Datenschutz & Sicherheit). Bitte fuer dieses Programm erlauben."
echo
python3 agent.py
