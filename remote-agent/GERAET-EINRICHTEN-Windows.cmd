@echo off
chcp 65001 >nul
title Alex Reviewit - Fernwartung (Geraet einrichten)
cd /d "%~dp0"
echo ============================================================
echo   Geraet dauerhaft fuer Fernwartung einrichten (unbeaufsichtigt)
echo ============================================================
echo.
echo Du brauchst den 6-stelligen EINRICHTUNGS-CODE aus dem Intranet
echo (Fernwartung -^> Geraet hinzufuegen). Nur der Inhaber kann ihn erzeugen.
echo.
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || ( echo [!] Bitte zuerst Python installieren (siehe SCHNELLHILFE). & pause & exit /b 1 )
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
set /p CODE=Einrichtungs-Code (6 Stellen): 
%PY% agent.py --enroll --code=%CODE%
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo Starte das Programm kuenftig automatisch bei der Anmeldung ...
schtasks /Create /TN "AlexReviewitFernwartung" /TR "cmd /c cd /d \"%~dp0\" && %PY% agent.py --service" /SC ONLOGON /RL LIMITED /F >nul 2>nul
if errorlevel 1 (
  echo [i] Autostart konnte nicht angelegt werden. Du kannst das Programm
  echo     manuell starten:  agent.py --service
) else (
  echo [ok] Autostart eingerichtet. Starte jetzt einmalig ...
  start "" %PY% agent.py --service
)
echo.
echo Fertig. Das Geraet ist jetzt im Intranet unter Fernwartung sichtbar.
pause
