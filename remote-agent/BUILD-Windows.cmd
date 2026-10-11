@echo off
chcp 65001 >nul
title Alex Reviewit Fernwartung - Programme bauen
cd /d "%~dp0"
echo ============================================================
echo   Baut zwei Programme:
echo     AlexReviewit-Schnellhilfe.exe   (QuickSupport)
echo     AlexReviewit-Fernwartung.exe    (Vollversion / Host)
echo ============================================================
echo.
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (
  echo [i] Python nicht gefunden - Installation ueber winget ...
  winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
  echo     Bitte Fenster schliessen und BUILD-Windows.cmd erneut starten.
  pause & exit /b 1
)
echo [1/3] Bausteine installieren ...
%PY% -m pip install --upgrade pip --disable-pip-version-check -q
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller
set COMMON=--noconfirm --clean --onefile --noconsole --version-file version.txt --add-data "assets;assets" --collect-all aiortc --collect-all av --collect-all aioice --collect-all pylibsrtp --collect-submodules pynput
echo [2/3] Schnellhilfe bauen ...
%PY% -m PyInstaller %COMMON% --name "AlexReviewit-Schnellhilfe" --icon "assets\icon.ico" schnellhilfe.py || (echo [!] Fehler & pause & exit /b 1)
echo [2/3] Vollversion bauen ...
%PY% -m PyInstaller %COMMON% --name "AlexReviewit-Fernwartung" --icon "assets\icon.ico" vollversion.py || (echo [!] Fehler & pause & exit /b 1)
echo [3/3] Fertigstellen ...
if not exist fertig mkdir fertig
copy /Y "dist\AlexReviewit-Schnellhilfe.exe" "fertig\" >nul
copy /Y "dist\AlexReviewit-Fernwartung.exe" "fertig\" >nul
echo.
echo [ok] Im Ordner 'fertig':
echo      AlexReviewit-Schnellhilfe.exe   -> an Kunden/Mitarbeiter weitergeben (zeigt Code)
echo      AlexReviewit-Fernwartung.exe    -> auf eigenen Geraeten installieren (Vollversion)
pause
