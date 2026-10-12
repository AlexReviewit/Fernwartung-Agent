; Inno-Setup-Skript – baut aus der Vollversion ein echtes Installationsprogramm
; (wie bei Firefox): installiert nach "Programme", legt einen Startmenü-Eintrag an
; und startet die Fernwartung auf Wunsch automatisch beim Anmelden.
; Die Versionsnummer kommt aus der CI:  ISCC Fernwartung.iss /DMyVersion=12
#ifndef MyVersion
  #define MyVersion "0"
#endif
#define AppName "Alex Reviewit Fernwartung"
#define AppExe "AlexReviewit-Fernwartung.exe"

[Setup]
AppId=AlexReviewitFernwartung
AppName={#AppName}
AppVersion={#MyVersion}
AppPublisher=Alex Reviewit
DefaultDirName={autopf}\Alex Reviewit Fernwartung
DefaultGroupName=Alex Reviewit Fernwartung
DisableProgramGroupPage=yes
DisableDirPage=auto
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=dist
OutputBaseFilename=AlexReviewit-Fernwartung-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=assets\icon.ico

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"
Name: "autostart"; Description: "Beim Anmelden automatisch starten (empfohlen – damit das Gerät dauerhaft erreichbar ist)"; GroupDescription: "Start:"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Alex Reviewit Fernwartung"; Filename: "{app}\{#AppExe}"
Name: "{group}\Alex Reviewit Fernwartung deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Alex Reviewit Fernwartung"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "AlexReviewitFernwartung"; ValueData: """{app}\{#AppExe}"""; \
  Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Fernwartung jetzt einrichten und starten"; Flags: nowait postinstall skipifsilent
