<div align="center">

![Alex Reviewit – Fernwartung](docs/banner.png)

Bildschirme sehen und Maus/Tastatur steuern – **direkt im Browser, Ende‑zu‑Ende verschlüsselt.**
Das eigene Fernwartungs‑Tool für das Intranet von Alex Reviewit.

[![Neueste Version](https://img.shields.io/github/v/release/AlexReviewit/Fernwartung-Agent?label=Version&sort=semver&color=8E7CFF)](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest)
&nbsp;[![Build](https://github.com/AlexReviewit/Fernwartung-Agent/actions/workflows/build-fernwartung.yml/badge.svg)](https://github.com/AlexReviewit/Fernwartung-Agent/actions/workflows/build-fernwartung.yml)
&nbsp;![Windows & macOS](https://img.shields.io/badge/Windows%20%26%20macOS-5DADFF)

**[⬇️ Download](#-download)** · **[🚀 Schnellstart](#-schnellstart)** · **[📘 Änderungen](CHANGELOG.md)**

</div>

<br>

## ⬇️ Download

> 💡 Am einfachsten direkt im Intranet unter **Fernwartung** – dort stehen die passenden Knöpfe.

|  | Windows | macOS |
|:--|:--:|:--:|
| ⚡ **Schnellhilfe** – spontane Hilfe, keine Installation | **[.exe](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Schnellhilfe.exe)** | **[.pkg](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Schnellhilfe.pkg)** |
| 💻 **Vollversion** – eigene Geräte dauerhaft | **[Installer](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Fernwartung-Setup.exe)** | **[Installer](https://github.com/AlexReviewit/Fernwartung-Agent/releases/latest/download/AlexReviewit-Fernwartung.pkg)** |

<br>

## 🚀 Schnellstart

**Spontane Hilfe** → *Schnellhilfe* starten, den 6‑stelligen Code vorlesen, fertig.

**Eigenes Gerät dauerhaft** → *Vollversion*‑Installer ausführen → beim ersten Start den
**Einrichtungs‑Code** aus dem Intranet eingeben *(kein Passwort nötig)* → im Programm wählen,
**wer zugreifen darf**.

<br>

## ✨ Auf einen Blick

- 🔒 **Ende‑zu‑Ende verschlüsselt** – Bild & Steuerung laufen direkt zwischen Browser und Gerät
- ✅ Zugriff nur nach **Zustimmung** oder nach deiner eingestellten Regel
- 🆔 **Geräte‑ID + Passwort** wie bei TeamViewer · feste oder Einmal‑Passwörter
- 🔄 **Automatisches Update** mit einem Klick
- 📝 Jede Sitzung wird **protokolliert**

<br>

<details>
<summary><b>🔑 Zugriffsregeln der Vollversion</b></summary>

<br>

| Regel | Bedeutung |
|:--|:--|
| **Fragen** | Bei jeder Verbindung wird am Gerät zuerst gefragt |
| **Passwort – fest** | Nur mit deinem festen Passwort, ohne Nachfrage |
| **Passwort – einmal** | Zufalls‑Passwort, wird angezeigt und wechselt nach jeder Sitzung |
| **Automatisch** | Ohne Nachfrage – nur für eigene, sichere Geräte |
| **Gesperrt** | Keine eingehenden Verbindungen |

Das Programmfenster zeigt außerdem die große **Geräte‑ID** (zum Kopieren), den **Live‑Status**
und den **letzten Zugriff**.

</details>

<details>
<summary><b>🎛️ Funktionen während einer Sitzung</b></summary>

<br>

- Volle Steuerung oder **„Nur zusehen“**
- Mehrere Bildschirme umschalten
- Dateien senden · Zwischenablage · Strg + Alt + Entf
- Chat mit Zeitstempel und Absender

</details>

<details>
<summary><b>🔄 Automatische Updates</b></summary>

<br>

Die Vollversion prüft von selbst auf neue Versionen. Ist eine da, erscheint
**„Version X ist verfügbar“** mit **„Jetzt aktualisieren“** – das Programm lädt den Installer
selbst herunter, startet ihn und schließt sich. Mit **„Nach Updates suchen“** geht es auch manuell.

> Damit Updates und Downloads für alle funktionieren, muss dieses Projekt **öffentlich** sein.

</details>

<details>
<summary><b>🔒 Sicherheit</b></summary>

<br>

- Verschlüsselt per **WebRTC / DTLS‑SRTP**, direkt zwischen Techniker und Gerät.
- Im Passwort‑Modus prüft der Server das Passwort, **bevor** eine Sitzung entsteht
  (mit Sperre nach mehreren Fehlversuchen).
- Zugriff auf die Seite nur mit **Microsoft‑Anmeldung** + Berechtigung „Fernsteuerung“.
- In diesem Projekt liegen **keine Passwörter oder Schlüssel** – die liegen sicher in Cloudflare.

</details>

<details>
<summary><b>🛠️ Für Entwickler</b></summary>

<br>

Jeder Push nach `main`, der `remote-agent/` ändert, baut automatisch und veröffentlicht zwei
Release‑Einträge: **„⭐ Neueste Version“** (feste Download‑Links) und **„Version N“**
(fortlaufend nummeriert, 1, 2, 3 … – alte bleiben erhalten). Die Versionsnummer wird beim
Bauen ins Programm geschrieben, damit das Auto‑Update sie vergleichen kann.

| Datei | Zweck |
|:--|:--|
| `remote-agent/agent.py` | Die ganze Logik (Signaling, Bildschirm, Steuerung, Fenster, Update) |
| `remote-agent/schnellhilfe.py` · `vollversion.py` | Einstiegspunkte |
| `remote-agent/Fernwartung.iss` | Windows‑Installer (Inno Setup) |
| `.github/workflows/build-fernwartung.yml` | Baut & veröffentlicht automatisch |

Lokal bauen: `remote-agent/BUILD-Windows.cmd` bzw. `BUILD-Mac.command`
(Details in `remote-agent/BAUEN-LIES-MICH.txt`).

</details>

<br>

<div align="center"><sub>© Alex Reviewit · Fernwartung für intranet.alexreviewit.at</sub></div>
