#!/bin/bash
cd "$(dirname "$0")"
echo "============================================================"
echo "  Baut  Schnellhilfe  und  Vollversion  (.app + .pkg)"
echo "============================================================"
command -v python3 >/dev/null 2>&1 || { echo "[!] Python 3 fehlt (python.org)."; read -n1 -s -r; exit 1; }
echo "[1/4] Bausteine installieren ..."
python3 -m pip install --upgrade pip --disable-pip-version-check -q
python3 -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller
COMMON="--noconfirm --clean --windowed --icon assets/icon.icns --add-data assets:assets --collect-all aiortc --collect-all av --collect-all aioice --collect-all pylibsrtp --collect-submodules pynput"
echo "[2/4] Schnellhilfe bauen ..."
python3 -m PyInstaller $COMMON --name "AlexReviewit-Schnellhilfe" --osx-bundle-identifier at.alexreviewit.fernwartung.quick schnellhilfe.py || { echo "[!] Fehler"; read -n1 -s -r; exit 1; }
echo "[3/4] Vollversion bauen ..."
python3 -m PyInstaller $COMMON --name "AlexReviewit-Fernwartung" --osx-bundle-identifier at.alexreviewit.fernwartung vollversion.py || { echo "[!] Fehler"; read -n1 -s -r; exit 1; }
echo "[4/4] .pkg bauen ..."
mkdir -p fertig
for N in "AlexReviewit-Schnellhilfe" "AlexReviewit-Fernwartung"; do
  [ -n "$CODESIGN_ID" ] && codesign --deep --force --options runtime --sign "$CODESIGN_ID" "dist/$N.app"
  pkgbuild --install-location /Applications --component "dist/$N.app" "fertig/$N.pkg" && echo "   fertig/$N.pkg"
  cp -R "dist/$N.app" fertig/ 2>/dev/null
done
echo
echo "[ok] Im Ordner 'fertig': Schnellhilfe + Vollversion als .app und .pkg."
echo "Hinweis Gatekeeper/Signatur: siehe BAUEN-LIES-MICH.txt."
read -n1 -s -r -p "Taste druecken ..."
