@echo off
chcp 65001 >nul
title Alex Reviewit - Fernwartung (Schnellhilfe)
cd /d "%~dp0"
echo ============================================================
echo   Alex Reviewit - Fernwartung / Schnellhilfe
echo ============================================================
echo.
echo Dieses Fenster laedt beim ersten Mal kurz die noetigen Bausteine
echo und zeigt dann einen 6-stelligen Code an. Diesen Code der Person
echo nennen, die hilft. Bild und Steuerung starten erst nach deiner
echo ausdruecklichen Zustimmung.
echo.
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (
  echo [!] Python ist nicht installiert.
  echo     Bitte einmalig von https://www.python.org/downloads/ installieren
  echo     ^(Haken "Add python.exe to PATH" setzen^) und dann neu starten.
  pause & exit /b 1
)
echo Installiere/aktualisiere Bausteine ^(nur beim ersten Mal noetig^) ...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
echo.
echo Starte Schnellhilfe ...
%PY% agent.py
pause
