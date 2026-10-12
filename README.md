<div align="center">

# 🖥️ Alex Reviewit – Fernwartung

**Das eigene Fernwartungs-Tool von Alex Reviewit – im Stil von TeamViewer & AnyDesk, nur einfacher.**
Bildschirme sehen und Maus/Tastatur steuern, direkt im Browser – Ende‑zu‑Ende verschlüsselt.

[![Build](https://github.com/AlexReviewit/Fernwartung-Agent/actions/workflows/build-fernwartung.yml/badge.svg)](https://github.com/AlexReviewit/Fernwartung-Agent/actions/workflows/build-fernwartung.yml)
[![Neueste Version](https://img.shields.io/github/v/release/AlexReviewit/Fernwartung-Agent?label=neueste%20Version&sort=semver&color=5DADFF)](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest)
![Windows & macOS](https://img.shields.io/badge/f%C3%BCr-Windows%20%26%20macOS-8E7CFF)
![Verschlüsselt](https://img.shields.io/badge/🔒-Ende--zu--Ende%20verschlüsselt-5BD6A0)

</div>

---

## Was ist das?

Ein kleines Programm, mit dem sich berechtigte Personen aus dem Intranet
**[intranet.alexreviewit.at](https://intranet.alexreviewit.at/fernwartung)** mit einem
Computer verbinden können – zum Zusehen oder zur vollen Steuerung. Die Verbindung läuft
**direkt** zwischen Techniker und Gerät und ist dabei **verschlüsselt**; das Intranet
vermittelt nur den Verbindungsaufbau.

> Es verbindet sich **nie von selbst**. Zugriff gibt es nur nach Zustimmung am Gerät bzw.
> nach der Regel, die du im Programm einstellst – und während jeder Sitzung läuft ein
> deutlich sichtbares Hinweis‑Banner, das jederzeit trennen kann.

## Zwei Programme – für zwei Situationen

| | ⚡ **Schnellhilfe** | 💻 **Vollversion** |
|---|---|---|
| Wofür? | Spontane Hilfe für jemanden | Eigene Geräte & Server dauerhaft erreichbar |
| Installation | Keine – einfach starten | Richtiges Setup (wie bei Firefox) |
| Verbinden über | 6‑stelligen Code vorlesen | Geräte‑ID (+ Passwort) |
| Zugriff | Nur mit Zustimmung am Gerät | Regel frei wählbar (siehe unten) |
| Vorbild | TeamViewer QuickSupport | TeamViewer/AnyDesk Host |

## Download

> **Für die meisten:** Die Programme bekommst du am einfachsten direkt im Intranet unter
> **Fernwartung** – dort sind die passenden Knöpfe für Windows und Mac.

Oder direkt hier (immer die neueste Version):

| | Windows | macOS |
|---|---|---|
| ⚡ Schnellhilfe | [Herunterladen](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Schnellhilfe.exe) | [Herunterladen](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Schnellhilfe.pkg) |
| 💻 Vollversion | [Installer](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Fernwartung-Setup.exe) | [Installer](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Fernwartung.pkg) |

Alle Versionen (auch ältere) findest du unter **[Releases](https://github.com/AlexReviewit/Fernwartung-Agent/releases)**.

## Vollversion einrichten

1. **Installer** herunterladen und ausführen → das Programm landet unter „Programme“ und
   startet auf Wunsch automatisch mit.
2. Beim ersten Start den **6‑stelligen Einrichtungs‑Code** aus dem Intranet eingeben
   (Fernwartung → „Gerät hinzufügen“). **Ein Passwort ist dabei nicht nötig.**
3. Im Programm einstellen, **wer zugreifen darf**:

| Regel | Bedeutung |
|---|---|
| **Fragen** | Bei jeder Verbindung wird am Gerät zuerst gefragt |
| **Passwort – fest** | Zugriff nur mit deinem festen Passwort, ohne Nachfrage |
| **Passwort – einmal** | Zufalls‑Passwort, wird angezeigt und wechselt nach jeder Sitzung |
| **Automatisch** | Ohne Nachfrage – nur für eigene, sichere Geräte |
| **Gesperrt** | Keine eingehenden Verbindungen |

## Funktionen in der Sitzung

- 🎛️ Volle Steuerung oder **„Nur zusehen“**
- 🖥️ Mehrere Bildschirme umschalten
- 📁 Dateien senden · 📋 Zwischenablage · ⌨️ Strg+Alt+Entf
- 💬 Chat mit Zeitstempel und Absender
- 🔄 Die Vollversion meldet **Updates** selbst und verlinkt auf die neueste Version

## Sicherheit

- 🔒 **Ende‑zu‑Ende verschlüsselt** (WebRTC / DTLS‑SRTP) – direkt zwischen Techniker und Gerät.
- ✅ Zugriff nur nach **Zustimmung** bzw. nach deiner eingestellten Regel.
- 🔑 Zugriffs‑Passwort gegen Ausprobieren geschützt (Sperre nach mehreren Fehlversuchen).
- 📝 Jede Sitzung wird **protokolliert** (Wer? Wann? Welches Gerät?).
- 🙈 In diesem Projekt liegen **keine Passwörter oder Schlüssel** – die liegen sicher in Cloudflare.

---

<details>
<summary><b>Für Entwickler / zum Selberbauen</b></summary>

### Automatisch in der GitHub‑Cloud (empfohlen)
Jeder Push nach `main`, der `remote-agent/` ändert, baut automatisch und veröffentlicht:

- **`Neueste Version`** – rollt immer auf den aktuellsten Build (feste Download‑Links).
- **`Version N`** – eine neue, fortlaufend nummerierte Version (1, 2, 3 …). Alte bleiben erhalten.

Die Versionsnummer wird beim Bauen ins Programm geschrieben (`build.txt`), damit das
automatische Update sie vergleichen kann (`remote-agent/version.json` als Release‑Anhang).

### Lokal bauen
```text
remote-agent/BUILD-Windows.cmd      (Windows)
remote-agent/BUILD-Mac.command      (macOS)
```
Details: `remote-agent/BAUEN-LIES-MICH.txt`.

### Aufbau
| Datei | Zweck |
|---|---|
| `remote-agent/agent.py` | Die ganze Logik (Signaling, Bildschirm, Steuerung, Oberfläche) |
| `remote-agent/schnellhilfe.py` | Einstieg Schnellhilfe (QuickSupport) |
| `remote-agent/vollversion.py` | Einstieg Vollversion (Host) |
| `remote-agent/Fernwartung.iss` | Windows‑Installer (Inno Setup) |
| `.github/workflows/build-fernwartung.yml` | Baut & veröffentlicht automatisch |

</details>

<div align="center"><sub>© Alex Reviewit · Fernwartung für intranet.alexreviewit.at</sub></div>
