#!/bin/bash
cd "$(dirname "$0")"
echo "=== Geraet dauerhaft fuer Fernwartung einrichten (macOS) ==="
echo
if ! command -v python3 >/dev/null 2>&1; then echo "[!] Bitte zuerst Python 3 installieren."; read -n1 -s -r; exit 1; fi
python3 -m pip install --disable-pip-version-check -q -r requirements.txt
read -p "Einrichtungs-Code (6 Stellen, aus dem Intranet): " CODE
python3 agent.py --enroll --code="$CODE" || { read -n1 -s -r; exit 1; }
DIR="$(pwd)"
PLIST="$HOME/Library/LaunchAgents/at.alexreviewit.fernwartung.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>at.alexreviewit.fernwartung</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$DIR/agent.py</string><string>--service</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" 2>/dev/null && echo "[ok] Autostart eingerichtet und gestartet." || echo "[i] Autostart manuell: python3 agent.py --service"
echo "Fertig. Denke an die Rechte unter Datenschutz & Sicherheit (Bildschirmaufnahme + Bedienungshilfen)."
read -n1 -s -r -p "Taste druecken ..."
