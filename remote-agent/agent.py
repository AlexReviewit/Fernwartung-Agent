#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alex Reviewit – Fernwartung (Agent)
===================================
Eigenes Fernwartungs-Programm im Stil von TeamViewer / AnyDesk.

Modi:
  (ohne Argument)   Schnellhilfe: zeigt einen 6-stelligen Sitzungscode an.
  --enroll          Gerät einmalig dauerhaft einrichten (mit Code aus dem Intranet).
  --service         hinterlegtes Gerät laufen lassen (unbeaufsichtigt).

Es verbindet sich NIE von selbst. Bild/Steuerung starten erst nach
ausdrücklicher Zustimmung am Gerät (Schnellhilfe) bzw. nach der vom Inhaber
gesetzten Regel (hinterlegtes Gerät). Während einer Sitzung ist immer ein
sichtbares rotes Banner aktiv, das jederzeit trennen kann. Die Verbindung
(Bild + Steuerung) läuft Ende-zu-Ende verschlüsselt (WebRTC/DTLS-SRTP) direkt
zum Browser des Technikers; das Intranet vermittelt nur den Aufbau.

Abhängigkeiten (werden im fertigen .exe/.app mitgeliefert):
  aiortc av mss pynput aiohttp numpy   (+ tkinter, bei Python dabei)
"""

import argparse
import asyncio
import json
import os
import platform
import socket
import sys
import threading
import time

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
FROZEN = getattr(sys, "frozen", False)

# Hohe DPI unter Windows: sorgt dafür, dass die Mausposition exakt stimmt
if IS_WIN:
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

BASE_URL = os.environ.get("IR_REMOTE_URL", "https://intranet.alexreviewit.at").rstrip("/")
AGENT_EP = BASE_URL + "/api/remote/agent"
APP_NAME = "Alex Reviewit Fernwartung"
BRAND = "Alex Reviewit"
FPS = int(os.environ.get("IR_REMOTE_FPS", "12"))
POLL_SECS = 2.0


def _bundled_build():
    """Fortlaufende Versionsnummer (1, 2, 3 …). Wird beim Bauen in build.txt
    geschrieben und ins Programm gepackt. Beim lokalen Entwickeln fehlt sie."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base, "build.txt"), "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    except Exception:
        pass
    return "0"


AGENT_VERSION = _bundled_build()   # wird beim automatischen Update verglichen
RELEASE_BASE = os.environ.get("IR_RELEASE_BASE", "https://github.com/AlexanderEdler/Fernwartung-Agent/releases/latest/download")
UPDATE_EVERY = 6 * 3600          # alle 6 Stunden auf neue Version prüfen


def resource_path(rel):
    """Pfad zu beigelegten Dateien – funktioniert auch im gebündelten .exe/.app."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ---------------------------------------------------------------------------
# Konfiguration für hinterlegte Geräte
# ---------------------------------------------------------------------------
def config_dir():
    if IS_WIN:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    d = os.path.join(base, "AlexReviewitFernwartung")
    os.makedirs(d, exist_ok=True)
    return d


CONFIG_FILE = os.path.join(config_dir(), "device.json")


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


def update_config(**kw):
    cfg = load_config(); cfg.update(kw); save_config(cfg); return cfg


def gen_password(n=6):
    """Gut lesbares Zufallspasswort (ohne verwechselbare Zeichen wie 0/O, 1/l)."""
    import secrets
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


def device_label():
    try:
        return socket.gethostname()
    except Exception:
        return "Gerät"


def os_label():
    name = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(platform.system(), platform.system())
    return (name + " " + platform.release())[:40]


# ---------------------------------------------------------------------------
# Automatisches Update – prüft version.json im GitHub-Repo
# ---------------------------------------------------------------------------
VERSION_URL = os.environ.get(
    "IR_VERSION_URL",
    # Datei liegt dem neuesten Release bei und wird bei jedem Bau automatisch
    # aktualisiert – so muss nie etwas von Hand geändert werden.
    "https://github.com/AlexanderEdler/Fernwartung-Agent/releases/latest/download/version.json",
)


def _ver_tuple(v):
    out = []
    for part in str(v).split("."):
        try:
            out.append(int(part))
        except Exception:
            out.append(0)
    return tuple(out)


def check_update():
    """Liefert (neue_version, download_seite) wenn eine neuere Version existiert, sonst None."""
    try:
        import urllib.request
        req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "AlexReviewit-Fernwartung"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = str(data.get("version", "")).strip()
        if latest and _ver_tuple(latest) > _ver_tuple(AGENT_VERSION):
            page = data.get("page") or "https://github.com/AlexanderEdler/Fernwartung-Agent/releases/latest"
            return (latest, page)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# HTTP-Signaling (nur Verbindungsaufbau; keine Bilddaten)
# ---------------------------------------------------------------------------
import aiohttp  # noqa: E402


class Signal:
    def __init__(self, session):
        self.s = session

    async def call(self, payload):
        async with self.s.post(AGENT_EP, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as r:
            try:
                data = await r.json()
            except Exception:
                data = {"error": "ungültige Antwort (%s)" % r.status}
            if r.status >= 400:
                raise RuntimeError(data.get("error", "Fehler %s" % r.status))
            return data


# ---------------------------------------------------------------------------
# Bildschirm als WebRTC-Video
# ---------------------------------------------------------------------------
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer  # noqa: E402
from aiortc.mediastreams import VideoStreamTrack  # noqa: E402
import av  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402


class ScreenTrack(VideoStreamTrack):
    """Erfasst fortlaufend den primären Bildschirm und liefert ihn als Videostrom."""

    def __init__(self, monitor_index=1):
        super().__init__()
        self._sct = mss.mss()
        # Liste echter Bildschirme (monitors[0] ist der Gesamtbereich -> weglassen)
        self.monitors = self._sct.monitors[1:] or [self._sct.monitors[0]]
        self.index = min(max(0, monitor_index - 1), len(self.monitors) - 1)
        self.monitor = self.monitors[self.index]
        self.width = self.monitor["width"]
        self.height = self.monitor["height"]
        self._interval = 1.0 / max(5, FPS)
        self._last = 0.0
        self.black_frames = 0   # für macOS-Berechtigungs-Hinweis

    def monitor_list(self):
        primary = None
        try:
            primary = self._sct.monitors[0]
        except Exception:
            pass
        out = []
        for m in self.monitors:
            out.append({"w": m["width"], "h": m["height"],
                        "primary": bool(primary and m.get("left", 0) == 0 and m.get("top", 0) == 0)})
        return out

    def set_monitor(self, i):
        if 0 <= i < len(self.monitors):
            self.index = i
            self.monitor = self.monitors[i]
            self.width = self.monitor["width"]
            self.height = self.monitor["height"]

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        wait = self._interval - (time.time() - self._last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.time()
        img = self._sct.grab(self.monitor)
        frame = np.frombuffer(img.rgb, dtype=np.uint8).reshape(img.height, img.width, 3)
        if IS_MAC:
            # ohne Bildschirmaufnahme-Recht liefert macOS nur schwarze/leere Bilder
            if int(frame[:: max(1, img.height // 8), :: max(1, img.width // 8)].max()) < 6:
                self.black_frames += 1
        vf = av.VideoFrame.from_ndarray(frame, format="rgb24")
        vf.pts = pts
        vf.time_base = time_base
        return vf


# ---------------------------------------------------------------------------
# Maus & Tastatur
# ---------------------------------------------------------------------------
from pynput import mouse as pmouse, keyboard as pkeyboard  # noqa: E402

_mouse = pmouse.Controller()
_kbd = pkeyboard.Controller()
_BTN = {0: pmouse.Button.left, 1: pmouse.Button.middle, 2: pmouse.Button.right}
_SPECIAL = {
    "Enter": pkeyboard.Key.enter, "Backspace": pkeyboard.Key.backspace, "Tab": pkeyboard.Key.tab,
    "Escape": pkeyboard.Key.esc, " ": pkeyboard.Key.space, "Delete": pkeyboard.Key.delete,
    "ArrowUp": pkeyboard.Key.up, "ArrowDown": pkeyboard.Key.down, "ArrowLeft": pkeyboard.Key.left,
    "ArrowRight": pkeyboard.Key.right, "Home": pkeyboard.Key.home, "End": pkeyboard.Key.end,
    "PageUp": pkeyboard.Key.page_up, "PageDown": pkeyboard.Key.page_down, "Insert": pkeyboard.Key.insert,
    "CapsLock": pkeyboard.Key.caps_lock, "Control": pkeyboard.Key.ctrl, "Alt": pkeyboard.Key.alt,
    "Shift": pkeyboard.Key.shift, "Meta": pkeyboard.Key.cmd, "OS": pkeyboard.Key.cmd,
}
for _i in range(1, 13):
    _SPECIAL["F%d" % _i] = getattr(pkeyboard.Key, "f%d" % _i)


def _to_key(name):
    if not name:
        return None
    if name in _SPECIAL:
        return _SPECIAL[name]
    if len(name) == 1:
        return name
    return None


class InputHandler:
    def __init__(self, track):
        self.track = track

    def _xy(self, m):
        x = int(max(0.0, min(1.0, m.get("x", 0))) * self.track.width) + self.track.monitor.get("left", 0)
        y = int(max(0.0, min(1.0, m.get("y", 0))) * self.track.height) + self.track.monitor.get("top", 0)
        return x, y

    def handle(self, m):
        t = m.get("t")
        try:
            if t == "m":
                _mouse.position = self._xy(m)
            elif t == "d":
                _mouse.position = self._xy(m); _mouse.press(_BTN.get(m.get("b", 0), pmouse.Button.left))
            elif t == "u":
                _mouse.position = self._xy(m); _mouse.release(_BTN.get(m.get("b", 0), pmouse.Button.left))
            elif t == "w":
                dx = -1 if m.get("dx", 0) > 0 else (1 if m.get("dx", 0) < 0 else 0)
                dy = -1 if m.get("dy", 0) > 0 else (1 if m.get("dy", 0) < 0 else 0)
                _mouse.scroll(dx, dy)
            elif t == "k":
                k = _to_key(m.get("k"))
                if k is None:
                    return
                _kbd.press(k) if m.get("down") else _kbd.release(k)
            elif t == "txt":
                _kbd.type(str(m.get("s", ""))[:500])
            elif t == "combo" and m.get("name") == "cad":
                for key in (pkeyboard.Key.ctrl, pkeyboard.Key.alt, pkeyboard.Key.delete):
                    _kbd.press(key)
                for key in (pkeyboard.Key.delete, pkeyboard.Key.alt, pkeyboard.Key.ctrl):
                    _kbd.release(key)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Oberfläche (tkinter) – im Stil der beiden Vorbilder: klares Hauptfenster,
# großer Code, Status; Zustimmungsdialog; dauerhaftes Sitzungs-Banner.
# ---------------------------------------------------------------------------
import tkinter as tk  # noqa: E402
from tkinter import font as tkfont  # noqa: E402

# Farben aus dem Intranet (dunkles Design): bg #11141F, Text #F3F6FB,
# Akzent Blau→Lila→Pink. So wirken die Programme wie die Webseite.
BG = "#11141F"; PANEL = "#171C2B"; CARD = "#1E2436"; FG = "#F3F6FB"
ACC = "#8E7CFF"; ACC2 = "#5DADFF"; PINK = "#E0689B"
OK = "#5BD6A0"; RED = "#E0485F"; MUT = "#B9C4D6"; FAINT = "#6B7488"; LINE = "#283460"
GRAD = ["#5DADFF", "#8E7CFF", "#E0689B"]   # Signatur-Verlauf der Webseite

_FONT_FAMILY = None


def ui_font(size, weight="normal"):
    """Schriftart im Webseiten-Stil (Manrope, sonst die beste System-Schrift)."""
    global _FONT_FAMILY
    if _FONT_FAMILY is None:
        try:
            fams = set(tkfont.families())
        except Exception:
            fams = set()
        for cand in ("Manrope", "Segoe UI Variable", "Segoe UI", "SF Pro Text",
                     "SF Pro Display", "Helvetica Neue", "Inter", "Arial"):
            if cand in fams:
                _FONT_FAMILY = cand
                break
        else:
            _FONT_FAMILY = "TkDefaultFont"
    return tkfont.Font(family=_FONT_FAMILY, size=size, weight=weight)


def _lerp(a, b, t):
    return int(round(a + (b - a) * t))


def _hex(c):
    return (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))


def _grad_color(t):
    """Farbe im 3-Stopp-Verlauf (0..1): Blau → Lila → Pink."""
    stops = [_hex(c) for c in GRAD]
    if t <= 0.5:
        u = t / 0.5; a, b = stops[0], stops[1]
    else:
        u = (t - 0.5) / 0.5; a, b = stops[1], stops[2]
    return "#%02x%02x%02x" % (_lerp(a[0], b[0], u), _lerp(a[1], b[1], u), _lerp(a[2], b[2], u))


def gradient_header(parent, width, title, subtitle=None, height=64):
    """Verlaufs-Kopfzeile wie der Hero/KI-Bereich der Webseite."""
    cv = tk.Canvas(parent, width=width, height=height, highlightthickness=0, bd=0, bg=BG)
    for x in range(width):
        cv.create_line(x, 0, x, height, fill=_grad_color(x / max(1, width - 1)))
    cv.create_text(22, height // 2 - (8 if subtitle else 0), anchor="w", text=title,
                   fill="#FFFFFF", font=ui_font(15, "bold"))
    if subtitle:
        cv.create_text(22, height // 2 + 12, anchor="w", text=subtitle,
                       fill="#F3F0FF", font=ui_font(9))
    return cv


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    """Abgerundetes Rechteck auf einem Canvas (für Karten im Webseiten-Look)."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def _set_icon(win):
    try:
        if IS_WIN:
            win.iconbitmap(resource_path(os.path.join("assets", "icon.ico")))
        else:
            win._icon_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "icon-128.png")))
            win.iconphoto(True, win._icon_img)
    except Exception:
        pass


class UI:
    def __init__(self, mode):
        self.mode = mode
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        _set_icon(self.root)
        self.main = None
        self.banner = None
        self.code_lbl = None
        self.status_lbl = None
        self.status_dot = None

    # ---- Hauptfenster (Schnellhilfe) ----
    def show_main(self, on_close):
        if self.main and self.main.winfo_exists():
            return
        W = 420
        w = self.main = tk.Toplevel(self.root)
        w.title(APP_NAME); w.configure(bg=BG); w.resizable(False, False)
        _set_icon(w)
        w.protocol("WM_DELETE_WINDOW", on_close)
        pad = tk.Frame(w, bg=BG); pad.pack()
        gradient_header(pad, W, "  " + BRAND, "Fernwartung · Schnellhilfe").pack()
        tk.Label(pad, text="Nenne diesen Code der Person, die dir hilft.", bg=BG, fg=MUT,
                 font=ui_font(11)).pack(padx=34, pady=(18, 12))
        # Code-Karte (abgerundet, im Webseiten-Look)
        cc = tk.Canvas(pad, width=W - 68, height=138, bg=BG, highlightthickness=0, bd=0)
        cc.pack(padx=34, pady=(0, 12))
        cw = W - 68
        round_rect(cc, 1, 1, cw - 1, 137, 18, fill=CARD, outline=LINE)
        cc.create_text(cw // 2, 24, text="SITZUNGSCODE", fill=ACC2, font=ui_font(9, "bold"))
        self._codec = cc
        self.code_lbl = tk.Label(cc, text="– – – – – –", bg=CARD, fg=FG, font=ui_font(40, "bold"))
        cc.create_window(cw // 2, 70, window=self.code_lbl)
        self.copy_btn = tk.Button(cc, text="Code kopieren", command=self._copy_code, bg=PANEL, fg=FG,
                                  activebackground="#2A3150", relief="flat", padx=14, pady=5,
                                  font=ui_font(10, "bold"), cursor="hand2", bd=0)
        cc.create_window(cw // 2, 112, window=self.copy_btn)
        # Status
        st = tk.Frame(pad, bg=BG); st.pack(padx=34, pady=(2, 6))
        self.status_dot = tk.Label(st, text="●", bg=BG, fg="#F5B14C", font=ui_font(11)); self.status_dot.pack(side="left", padx=(0, 7))
        self.status_lbl = tk.Label(st, text="Bereit – warte auf Verbindung …", bg=BG, fg=MUT, font=ui_font(10)); self.status_lbl.pack(side="left")
        tk.Label(pad, text="Niemand sieht deinen Bildschirm, bevor du zustimmst.\nDieses Fenster kannst du jederzeit schließen.",
                 bg=BG, fg=MUT, font=ui_font(9), justify="center").pack(padx=34, pady=(8, 6))
        tk.Label(pad, text="🔒 Ende-zu-Ende verschlüsselt · " + BASE_URL.replace("https://", ""),
                 bg=BG, fg=FAINT, font=ui_font(8)).pack(pady=(0, 18))
        self._center(w, 3)
        w.attributes("-topmost", True); w.deiconify(); w.attributes("-topmost", False)

    def _copy_code(self):
        try:
            code = (self.code_lbl.cget("text") or "").replace(" ", "")
            self.root.clipboard_clear(); self.root.clipboard_append(code)
            self.copy_btn.configure(text="Kopiert ✓")
            self.root.after(1500, lambda: self.copy_btn.configure(text="Code kopieren"))
        except Exception:
            pass

    def set_code(self, code):
        if self.code_lbl:
            self.code_lbl.configure(text=code[:3] + " " + code[3:])

    def set_status(self, text, color=MUT, dot="#F5B14C"):
        if self.status_lbl:
            try:
                self.status_lbl.configure(text=text, fg=color); self.status_dot.configure(fg=dot)
            except Exception:
                pass

    # ---- Zustimmungsdialog ----
    def ask_consent(self, who, timeout_s, result):
        dlg = tk.Toplevel(self.root); dlg.title("Fernwartungs-Anfrage"); dlg.configure(bg=BG); dlg.resizable(False, False)
        _set_icon(dlg); dlg.attributes("-topmost", True)
        gradient_header(dlg, 400, "  🔒  Fernwartungs-Anfrage", height=56).pack()
        tk.Label(dlg, text="%s\nmöchte deinen Bildschirm sehen und steuern." % who, bg=BG, fg=FG,
                 font=ui_font(12), justify="center").pack(padx=36, pady=(18, 4))
        tk.Label(dlg, text="Nur zustimmen, wenn du diese Hilfe gerade erwartest.", bg=BG, fg=MUT,
                 font=ui_font(9)).pack(padx=36, pady=(0, 12))
        countdown = tk.Label(dlg, text="", bg=BG, fg=MUT, font=ui_font(9)); countdown.pack()
        btns = tk.Frame(dlg, bg=BG); btns.pack(padx=36, pady=(10, 24))

        def answer(ok):
            result[0] = ok
            try:
                dlg.destroy()
            except Exception:
                pass

        tk.Button(btns, text="Ablehnen", command=lambda: answer(False), bg=PANEL, fg=FG, activebackground="#2A3150",
                  relief="flat", padx=22, pady=10, font=ui_font(11, "bold"), cursor="hand2", bd=0).pack(side="left", padx=9)
        tk.Button(btns, text="Zustimmen", command=lambda: answer(True), bg=OK, fg="#06281C", activebackground="#57e0a6",
                  relief="flat", padx=22, pady=10, font=ui_font(11, "bold"), cursor="hand2", bd=0).pack(side="left", padx=9)
        dlg.protocol("WM_DELETE_WINDOW", lambda: answer(False))
        self._center(dlg, 3)
        state = {"left": int(timeout_s)}

        def tick():
            if not dlg.winfo_exists() or result[0] is not None:
                return
            countdown.configure(text="Automatisch abgelehnt in %d s" % state["left"])
            state["left"] -= 1
            answer(False) if state["left"] < 0 else dlg.after(1000, tick)

        tick()

    # ---- Dauerhaftes Sitzungs-Banner ----
    def show_banner(self, who, on_disconnect):
        b = self.banner = tk.Toplevel(self.root)
        b.overrideredirect(True); b.configure(bg=RED); b.attributes("-topmost", True)
        try:
            b.attributes("-alpha", 0.96)
        except Exception:
            pass
        frm = tk.Frame(b, bg=RED); frm.pack(fill="both", expand=True, padx=14, pady=7)
        tk.Label(frm, text="●", bg=RED, fg="#FFFFFF", font=ui_font(12)).pack(side="left", padx=(2, 8))
        tk.Label(frm, text="Fernwartung aktiv – %s sieht und steuert diesen Bildschirm" % who,
                 bg=RED, fg="#FFFFFF", font=ui_font(10, "bold")).pack(side="left")
        tk.Button(frm, text="Trennen", command=on_disconnect, bg="#FFFFFF", fg=RED, relief="flat",
                  padx=14, pady=3, font=ui_font(10, "bold"), cursor="hand2", bd=0).pack(side="left", padx=14)
        b.update_idletasks()
        b.geometry("+%d+%d" % ((b.winfo_screenwidth() - b.winfo_width()) // 2, 8))
        self._pulse(b, 0)

    def _pulse(self, b, step):
        if not b.winfo_exists():
            return
        try:
            b.attributes("-alpha", 0.8 + 0.18 * abs(((step % 20) / 10.0) - 1))
        except Exception:
            pass
        b.after(80, lambda: self._pulse(b, step + 1))

    def hide_banner(self):
        if self.banner:
            try:
                self.banner.destroy()
            except Exception:
                pass
            self.banner = None

    # ---- Chat-Fenster (waehrend der Sitzung) ----
    def show_chat(self, on_send):
        if getattr(self, "chat", None) and self.chat.winfo_exists():
            self.chat.deiconify(); return
        w = self.chat = tk.Toplevel(self.root); w.title("Chat – Fernwartung"); w.configure(bg=BG)
        _set_icon(w)
        gradient_header(w, 360, "  💬  Chat", height=48).pack()
        self.chat_log = tk.Text(w, width=42, height=13, bg=CARD, fg=FG, relief="flat", wrap="word", state="disabled",
                                font=ui_font(10), padx=10, pady=8); self.chat_log.pack(padx=12, pady=(12, 6))
        self.chat_log.tag_configure("meta", foreground=FAINT, font=ui_font(8, "bold"))
        self.chat_log.tag_configure("me", foreground=ACC2)
        self.chat_log.tag_configure("them", foreground=FG)
        row = tk.Frame(w, bg=BG); row.pack(fill="x", padx=12, pady=(0, 12))
        ent = tk.Entry(row, bg=PANEL, fg=FG, relief="flat", insertbackground=FG, font=ui_font(11)); ent.pack(side="left", fill="x", expand=True, ipady=6)
        def go(_=None):
            t = ent.get().strip()
            if t:
                on_send(t); self.add_chat(t, True); ent.delete(0, "end")
        ent.bind("<Return>", go)
        tk.Button(row, text="Senden", command=go, bg=ACC, fg="#0C0A26", relief="flat",
                  font=ui_font(10, "bold"), cursor="hand2", bd=0, padx=12).pack(side="left", padx=(8, 0))
        w.protocol("WM_DELETE_WINDOW", w.withdraw)
        self._center(w, 2)

    def add_chat(self, text, me):
        try:
            if not getattr(self, "chat", None) or not self.chat.winfo_exists():
                return
            self.chat.deiconify()
            hh = time.strftime("%H:%M")
            self.chat_log.configure(state="normal")
            self.chat_log.insert("end", ("Du" if me else "Techniker") + " · " + hh + "\n", "meta")
            self.chat_log.insert("end", text + "\n", ("me" if me else "them"))
            self.chat_log.see("end"); self.chat_log.configure(state="disabled")
        except Exception:
            pass

    # ---- Status-Fenster der Vollversion (Host) ----
    MODES = [
        ("ask", "Fragen", "Bei jeder Verbindung wird hier am Gerät erst gefragt."),
        ("password", "Passwort", "Zugriff nur mit dem Zugriffs-Passwort – ohne Nachfrage."),
        ("allow", "Automatisch", "Verbindet sofort ohne Nachfrage – nur für eigene, sichere Geräte."),
        ("off", "Gesperrt", "Es sind keine eingehenden Verbindungen möglich."),
    ]

    def show_host(self, name, ident, cb):
        """cb: dict mit close, open, mode(mode), pwstyle(style), pwaction()"""
        W = 468
        self.host_ident = ident
        self._pw_plain = ""
        self._pw_style = "random"
        w = self.main = tk.Toplevel(self.root); w.title(APP_NAME + " – Vollversion"); w.configure(bg=BG); w.resizable(False, False)
        _set_icon(w)
        # Fenster schließen = in den Hintergrund (läuft weiter), nicht beenden
        w.protocol("WM_DELETE_WINDOW", w.iconify)
        pad = tk.Frame(w, bg=BG); pad.pack(fill="both", expand=True)
        gradient_header(pad, W, "  " + BRAND, "Fernwartung · Vollversion").pack()
        # Geräte-Karte (abgerundet) mit großer ID und Kopier-Knopf
        cw = W - 68
        cc = self._ident_cv = tk.Canvas(pad, width=cw, height=132, bg=BG, highlightthickness=0, bd=0); cc.pack(padx=34, pady=(16, 8))
        round_rect(cc, 1, 1, cw - 1, 131, 18, fill=CARD, outline=LINE)
        cc.create_text(22, 24, anchor="w", text="DIESES GERÄT", fill=ACC2, font=ui_font(9, "bold"))
        cc.create_text(22, 52, anchor="w", text=name, fill=FG, font=ui_font(17, "bold"))
        cc.create_text(22, 92, anchor="w", text="ID", fill=MUT, font=ui_font(9, "bold"))
        self._ident_item = cc.create_text(22, 110, anchor="w", text=ident, fill=ACC2, font=ui_font(16, "bold"))
        _copybtn = tk.Button(cc, text="ID kopieren", command=self._copy_ident, bg=PANEL, fg=FG, activebackground="#2A3150",
                             relief="flat", padx=12, pady=5, font=ui_font(9, "bold"), cursor="hand2", bd=0)
        cc.create_window(cw - 14, 101, anchor="e", window=_copybtn)
        # Live-Status + letzter Zugriff
        st = tk.Frame(pad, bg=BG); st.pack(padx=34, pady=(0, 2), anchor="w")
        self.status_dot = tk.Label(st, text="●", bg=BG, fg="#F5B14C", font=ui_font(10)); self.status_dot.pack(side="left", padx=(0, 6))
        self.status_lbl = tk.Label(st, text="Verbinde mit dem Intranet …", bg=BG, fg=MUT, font=ui_font(10)); self.status_lbl.pack(side="left")
        self.host_status = self.status_lbl   # Kompatibilität
        self.host_last = tk.Label(pad, text="Letzter Zugriff: noch keiner", bg=BG, fg=FAINT, font=ui_font(9)); self.host_last.pack(padx=34, anchor="w", pady=(0, 12))
        # Zugriffsregel (wie TeamViewer/AnyDesk, aber einfacher)
        tk.Label(pad, text="WER DARF ZUGREIFEN?", bg=BG, fg=MUT, font=ui_font(9, "bold")).pack(padx=34, anchor="w")
        seg = tk.Frame(pad, bg=LINE); seg.pack(padx=34, pady=(6, 4), fill="x")
        self._mode_btns = {}
        for i, (key, label, _hint) in enumerate(self.MODES):
            b = tk.Button(seg, text=label, command=lambda k=key: cb["mode"](k), bg=PANEL, fg=MUT, relief="flat",
                          padx=6, pady=8, font=ui_font(10, "bold"), cursor="hand2", bd=0)
            b.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 1, 0))
            seg.grid_columnconfigure(i, weight=1)
            self._mode_btns[key] = b
        self._mode_hint = tk.Label(pad, text="", bg=BG, fg=MUT, font=ui_font(9), wraplength=cw, justify="left")
        self._mode_hint.pack(padx=34, anchor="w", pady=(2, 8))
        # Passwort-Bereich (nur sichtbar bei Modus „Passwort“)
        self.pwpanel = tk.Frame(pad, bg=BG)
        styrow = tk.Frame(self.pwpanel, bg=BG); styrow.pack(anchor="w", fill="x")
        tk.Label(styrow, text="Passwort-Art:", bg=BG, fg=MUT, font=ui_font(9, "bold")).pack(side="left", padx=(0, 8))
        self._pwstyle_btns = {}
        for key, label in (("random", "Zufällig (pro Sitzung)"), ("fixed", "Fest")):
            b = tk.Button(styrow, text=label, command=lambda k=key: cb["pwstyle"](k), bg=PANEL, fg=MUT, relief="flat",
                          padx=10, pady=4, font=ui_font(9, "bold"), cursor="hand2", bd=0)
            b.pack(side="left", padx=(0, 6)); self._pwstyle_btns[key] = b
        disp = tk.Frame(self.pwpanel, bg=BG); disp.pack(anchor="w", fill="x", pady=(8, 0))
        self._pw_display = tk.Label(disp, text="—", bg=CARD, fg=FG, font=ui_font(19, "bold"), padx=14, pady=6); self._pw_display.pack(side="left")
        self._pw_copy = tk.Button(disp, text="Kopieren", command=self._copy_pw, bg=PANEL, fg=FG, relief="flat",
                                  padx=10, pady=6, font=ui_font(9, "bold"), cursor="hand2", bd=0); self._pw_copy.pack(side="left", padx=6)
        self._pw_action = tk.Button(disp, text="🔄 Neu", command=lambda: cb["pwaction"](), bg=PANEL, fg=FG, relief="flat",
                                    padx=10, pady=6, font=ui_font(9, "bold"), cursor="hand2", bd=0); self._pw_action.pack(side="left")
        self._pw_note = tk.Label(self.pwpanel, text="", bg=BG, fg=FAINT, font=ui_font(8), wraplength=cw, justify="left")
        self._pw_note.pack(anchor="w", pady=(6, 2))
        # Update-Hinweis (zunächst versteckt)
        self.update_bar = tk.Frame(pad, bg="#15321F")
        self._update_lbl = tk.Label(self.update_bar, text="", bg="#15321F", fg="#8CE0B4",
                                    font=ui_font(10, "bold")); self._update_lbl.pack(side="left", padx=(14, 8), pady=9)
        self._update_btn = tk.Button(self.update_bar, text="Herunterladen", bg=OK, fg="#06250F", relief="flat",
                                     padx=12, pady=4, font=ui_font(9, "bold"), cursor="hand2", bd=0); self._update_btn.pack(side="left", padx=(0, 12), pady=9)
        # Aktionen
        act = tk.Frame(pad, bg=BG); act.pack(padx=34, pady=(14, 6), fill="x")
        tk.Button(act, text="Intranet öffnen", command=cb["open"], bg=ACC, fg="#0C0A26", activebackground="#a99bff",
                  relief="flat", padx=12, pady=7, font=ui_font(10, "bold"), cursor="hand2", bd=0).pack(side="left")
        tk.Button(act, text="Im Hintergrund", command=w.iconify, bg=PANEL, fg=FG, activebackground="#2A3150",
                  relief="flat", padx=12, pady=7, font=ui_font(10, "bold"), cursor="hand2", bd=0).pack(side="left", padx=8)
        tk.Button(act, text="Beenden", command=cb["close"], bg=PANEL, fg=MUT, activebackground="#3A2130",
                  relief="flat", padx=12, pady=7, font=ui_font(10, "bold"), cursor="hand2", bd=0).pack(side="right")
        _vshow = ("Version " + AGENT_VERSION) if AGENT_VERSION != "0" else "Entwicklungs-Version"
        tk.Label(pad, text="🔒 Ende-zu-Ende verschlüsselt · " + _vshow, bg=BG, fg=FAINT,
                 font=ui_font(8)).pack(pady=(6, 14))
        self.set_host_mode("ask", False)
        self._center(w, 3); w.deiconify()

    def set_ident(self, pub_id):
        """ersetzt die angezeigte Geräte-ID durch die kurze Nummer (wie TeamViewer)."""
        try:
            digits = "".join(ch for ch in str(pub_id) if ch.isdigit())
            if not digits:
                return
            self.host_ident = digits
            pretty = digits
            if len(digits) == 9:
                pretty = digits[0:3] + " " + digits[3:6] + " " + digits[6:9]
            self._ident_cv.itemconfigure(self._ident_item, text=pretty)
        except Exception:
            pass

    def _copy_pw(self):
        try:
            if self._pw_plain:
                self.root.clipboard_clear(); self.root.clipboard_append(self._pw_plain)
                self._pw_copy.configure(text="Kopiert ✓")
                self.root.after(1400, lambda: self._pw_copy.configure(text="Kopieren"))
        except Exception:
            pass

    def set_pw_style(self, style):
        """Hebt die gewählte Passwort-Art hervor und passt Knöpfe/Hinweis an."""
        self._pw_style = style
        try:
            for key, b in getattr(self, "_pwstyle_btns", {}).items():
                on = key == style
                b.configure(bg=(ACC2 if on else PANEL), fg=("#06281C" if on else MUT))
            if style == "random":
                self._pw_action.configure(text="🔄 Neu")
                self._pw_copy.pack(side="left", padx=6)
                self._pw_note.configure(text="Das Passwort wechselt nach jeder Sitzung. Sag es der Person, die sich verbindet.")
            else:
                self._pw_action.configure(text="Ändern")
                self._pw_copy.pack_forget()
                self._pw_note.configure(text="Festes Passwort – bleibt gleich, bis du es änderst. Aus Sicherheitsgründen wird es nicht angezeigt.")
        except Exception:
            pass

    def set_pw_value(self, text):
        """Zeigt das aktuelle (zufällige) Passwort groß an; bei festem Passwort Punkte."""
        try:
            self._pw_plain = text if self._pw_style == "random" else ""
            self._pw_display.configure(text=(text if (self._pw_style == "random" and text) else ("●●●●●●" if self._pw_style == "fixed" else "—")))
        except Exception:
            pass

    def _copy_ident(self):
        try:
            self.root.clipboard_clear(); self.root.clipboard_append(getattr(self, "host_ident", ""))
            self.info(APP_NAME, "Geräte-ID kopiert.")
        except Exception:
            pass

    def set_host_mode(self, mode, has_pw):
        """Hebt die aktive Zugriffsregel hervor und zeigt den passenden Hinweis."""
        try:
            for key, b in getattr(self, "_mode_btns", {}).items():
                on = key == mode
                b.configure(bg=(ACC if on else PANEL), fg=("#0C0A26" if on else MUT))
            hint = dict((k, h) for k, _l, h in self.MODES).get(mode, "")
            self._mode_hint.configure(text=hint)
            # Passwort-Bereich nur bei Modus „Passwort“ zeigen
            if mode == "password":
                if not self.pwpanel.winfo_ismapped():
                    self.pwpanel.pack(padx=34, fill="x", pady=(0, 4), after=self._mode_hint)
            else:
                self.pwpanel.pack_forget()
        except Exception:
            pass

    def set_last_access(self, ts, by):
        try:
            if not ts:
                self.host_last.configure(text="Letzter Zugriff: noch keiner"); return
            import time as _t
            secs = max(0, int(_t.time()) - int(ts) // 1000 if ts > 10 ** 12 else int(_t.time()) - int(ts))
            if secs < 90:
                rel = "gerade eben"
            elif secs < 3600:
                rel = "vor %d Min." % (secs // 60)
            elif secs < 86400:
                rel = "vor %d Std." % (secs // 3600)
            else:
                rel = "vor %d Tagen" % (secs // 86400)
            self.host_last.configure(text="Letzter Zugriff: %s%s" % ((by + ", ") if by else "", rel))
        except Exception:
            pass

    def show_update(self, ver, page):
        """Zeigt den Update-Hinweis im Host-Fenster an."""
        try:
            import webbrowser
            self._update_lbl.config(text="⬆  Neue Version %s verfügbar" % ver)
            self._update_btn.config(command=lambda: webbrowser.open(page))
            self.update_bar.pack(padx=34, pady=(2, 6))
        except Exception:
            pass

    def ask_text(self, title, prompt, show=None):
        try:
            from tkinter import simpledialog
            return simpledialog.askstring(title, prompt, show=show, parent=self.root)
        except Exception:
            return None

    def info(self, title, text):
        try:
            from tkinter import messagebox
            messagebox.showinfo(title, text)
        except Exception:
            pass

    def _center(self, w, div=2):
        w.update_idletasks()
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        w.geometry("+%d+%d" % ((sw - w.winfo_width()) // 2, (sh - w.winfo_height()) // div))

    def run_soon(self, fn):
        self.root.after(0, fn)


# ---------------------------------------------------------------------------
# Netzwerk-/Sitzungslogik
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, ui, mode):
        self.ui = ui
        self.mode = mode
        self.ident = {}
        self.stop = False
        self.pc = None
        self.active_sid = None
        self._disconnect_evt = None
        self.loop = None
        self._mac_hint = False
        self.random_pw = None   # aktuelles Zufallspasswort (Vollversion)

    async def run(self):
        self.loop = asyncio.get_event_loop()
        async with aiohttp.ClientSession() as s:
            sig = Signal(s)
            if self.mode == "quick":
                reg = await sig.call({"action": "register", "name": device_label(), "os": os_label()})
                self.ident = {"code": reg["code"], "key": reg["key"]}
                self.ui.run_soon(lambda: self.ui.set_code(reg["code"]))
            else:
                cfg = load_config()
                if not cfg.get("device") or not cfg.get("token"):
                    raise RuntimeError("Dieses Gerät ist noch nicht eingerichtet (zuerst: --enroll).")
                self.ident = {"device": cfg["device"], "token": cfg["token"]}
                asyncio.ensure_future(self.update_loop())
            await self.poll_loop(sig)

    async def update_loop(self):
        """Prüft regelmäßig auf eine neue Version (nur Vollversion/hinterlegtes Gerät)."""
        await asyncio.sleep(5)
        while not self.stop:
            try:
                res = await self.loop.run_in_executor(None, check_update)
                if res:
                    ver, page = res
                    self.ui.run_soon(lambda v=ver, p=page: getattr(self.ui, "show_update", lambda *_: None)(v, p))
            except Exception:
                pass
            await asyncio.sleep(UPDATE_EVERY)

    async def poll_loop(self, sig):
        while not self.stop:
            try:
                payload = {"action": "poll"}
                payload.update(self.ident)
                if self.mode == "service":
                    payload["os"] = os_label()
                res = await sig.call(payload)
                self.ui.run_soon(lambda: self.ui.set_status("Bereit – warte auf Verbindung …", MUT, "#34D399"))
                sess = res.get("session")
                if sess and sess.get("sid") and sess["sid"] != self.active_sid:
                    await self.handle_session(sig, sess, res.get("unattended", "ask"))
            except Exception:
                self.ui.run_soon(lambda: self.ui.set_status("Verbinde mit dem Intranet …", "#F5B14C", "#F5B14C"))
            await asyncio.sleep(POLL_SECS)

    async def handle_session(self, sig, sess, unattended):
        sid = sess["sid"]; who = sess.get("byName", "Ein Techniker")
        self.ui.run_soon(lambda: self.ui.set_status("Anfrage von %s …" % who, ACC2, ACC2))
        allow = False
        if self.mode == "quick" or unattended == "ask":
            result = [None]
            self.ui.run_soon(lambda: self.ui.ask_consent(who, 30, result))
            while result[0] is None and not self.stop:
                await asyncio.sleep(0.2)
            allow = bool(result[0])
        elif unattended == "allow":
            allow = True
        if not allow:
            await sig.call(dict({"action": "decline", "sid": sid, "reason": "am Gerät abgelehnt"}, **self.ident))
            self.ui.run_soon(lambda: self.ui.set_status("Anfrage abgelehnt.", MUT, "#8A93A6"))
            return
        await sig.call(dict({"action": "accept", "sid": sid}, **self.ident))
        if hasattr(self.ui, "set_last_access"):
            self.ui.run_soon(lambda: self.ui.set_last_access(int(time.time()), who))
        try:
            await self.run_session(sig, sid, who)
        finally:
            self.active_sid = None
            self.ui.run_soon(self.ui.hide_banner)
            self.ui.run_soon(lambda: self.ui.set_status("Sitzung beendet. Bereit.", MUT, "#34D399"))
            if self.mode == "quick":
                try:
                    reg = await sig.call({"action": "register", "name": device_label(), "os": os_label()})
                    self.ident = {"code": reg["code"], "key": reg["key"]}
                    self.ui.run_soon(lambda: self.ui.set_code(reg["code"]))
                except Exception:
                    pass
            else:
                # Vollversion mit Zufallspasswort: nach jeder Sitzung ein neues erzeugen
                try:
                    if load_config().get("pwstyle") == "random":
                        await self.rotate_random_pw(sig)
                except Exception:
                    pass

    async def rotate_random_pw(self, sig):
        pw = gen_password()
        await sig.call(dict({"action": "setpw", "password": pw}, **self.ident))
        self.random_pw = pw
        if hasattr(self.ui, "set_pw_value"):
            self.ui.run_soon(lambda: (self.ui.set_pw_style("random"), self.ui.set_pw_value(pw)))

    async def run_session(self, sig, sid, who):
        self.active_sid = sid
        self.ui.run_soon(lambda: self.ui.set_status("Verbindung wird aufgebaut …", ACC2, ACC2))
        off = await sig.call(dict({"action": "getOffer", "sid": sid}, **self.ident))
        offer = off.get("offer")
        if not offer:
            for _ in range(12):
                await asyncio.sleep(0.6)
                off = await sig.call(dict({"action": "getOffer", "sid": sid}, **self.ident))
                offer = off.get("offer")
                if offer:
                    break
        if not offer:
            raise RuntimeError("Kein Angebot erhalten")
        ice = [RTCIceServer(**srv) if isinstance(srv, dict) else RTCIceServer(urls=srv) for srv in off.get("ice", [])]
        self.pc = pc = RTCPeerConnection(RTCConfiguration(iceServers=ice) if ice else None)
        track = ScreenTrack()
        handler = InputHandler(track)
        pc.addTrack(track)
        self._disconnect_evt = asyncio.Event()

        self._dc = None
        recv = {}   # laufende Datei-Empfaenge

        def save_file(name, b64):
            import base64
            folder = os.path.join(os.path.expanduser("~"), "Desktop", "AlexReviewit-Empfangen")
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                folder = os.path.expanduser("~")
            safe = "".join(c for c in (name or "datei") if c not in '\\/:*?"<>|').strip() or "datei"
            path = os.path.join(folder, safe)
            n = 1
            while os.path.exists(path):
                base, ext = os.path.splitext(os.path.join(folder, safe)); path = "%s (%d)%s" % (base, n, ext); n += 1
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            return os.path.basename(path)

        def send_dc(o):
            try:
                if self._dc and self._dc.readyState == "open":
                    self._dc.send(json.dumps(o))
            except Exception:
                pass

        @pc.on("datachannel")
        def on_dc(channel):
            self._dc = channel

            @channel.on("message")
            def on_msg(message):
                try:
                    m = json.loads(message)
                except Exception:
                    return
                t = m.get("t")
                if t == "hello":
                    send_dc({"t": "mon", "list": track.monitor_list(), "cur": track.index})
                elif t == "setmon":
                    track.set_monitor(int(m.get("i", 0)))
                elif t == "clip":
                    self.ui.run_soon(lambda s=str(m.get("s", "")): self._set_clipboard(s))
                elif t == "chat":
                    self.ui.run_soon(lambda s=str(m.get("s", "")): (self.ui.show_chat(lambda x: send_dc({"t": "chat", "s": x})), self.ui.add_chat(s, False)))
                elif t == "file-begin":
                    recv[m.get("id")] = {"name": m.get("name", "datei"), "parts": []}
                elif t == "file-chunk":
                    r = recv.get(m.get("id"));  r and r["parts"].append(m.get("data", ""))
                elif t == "file-end":
                    r = recv.pop(m.get("id"), None)
                    if r:
                        try:
                            nm = save_file(r["name"], "".join(r["parts"]))
                            send_dc({"t": "file-ok", "name": nm})
                            self.ui.run_soon(lambda nm=nm: self.ui.add_chat("Datei empfangen: " + nm + "  (Ordner „AlexReviewit-Empfangen“ auf dem Schreibtisch)", False) if getattr(self.ui, "chat", None) else None)
                        except Exception:
                            pass
                else:
                    handler.handle(m)

        @pc.on("connectionstatechange")
        async def on_state():
            if pc.connectionState in ("failed", "closed", "disconnected"):
                self._disconnect_evt.set()

        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await self._ice_complete(pc)
        await sig.call(dict({"action": "answer", "sid": sid, "sdp": pc.localDescription.sdp}, **self.ident))
        self.ui.run_soon(lambda: self.ui.show_banner(who, self.request_disconnect))
        self.ui.run_soon(lambda: self.ui.set_status("Verbunden mit %s" % who, OK, OK))

        while not self.stop:
            if self._disconnect_evt.is_set():
                break
            if IS_MAC and not self._mac_hint and track.black_frames > 20:
                self._mac_hint = True
                self.ui.run_soon(lambda: self.ui.info(
                    "Bildschirmaufnahme erlauben",
                    "macOS überträgt noch kein Bild.\n\nBitte unter Systemeinstellungen → Datenschutz & Sicherheit →\n"
                    "Bildschirmaufnahme das Programm '%s' erlauben und danach neu starten.\n"
                    "Für die Steuerung zusätzlich 'Bedienungshilfen' erlauben." % APP_NAME))
            try:
                st = await sig.call(dict({"action": "state", "sid": sid}, **self.ident))
                if st.get("state") == "ended":
                    break
            except Exception:
                pass
            await asyncio.sleep(2.0)
        try:
            await sig.call(dict({"action": "end", "sid": sid, "reason": "beendet"}, **self.ident))
        except Exception:
            pass
        await pc.close()
        self.pc = None

    async def _ice_complete(self, pc):
        if pc.iceGatheringState == "complete":
            return
        evt = asyncio.Event()

        @pc.on("icegatheringstatechange")
        def _chg():
            if pc.iceGatheringState == "complete":
                evt.set()

        try:
            await asyncio.wait_for(evt.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            pass

    def _set_clipboard(self, text):
        try:
            self.ui.root.clipboard_clear(); self.ui.root.clipboard_append(text)
        except Exception:
            pass

    def request_disconnect(self):
        if self._disconnect_evt and self.loop:
            self.loop.call_soon_threadsafe(self._disconnect_evt.set)

    def request_quit(self):
        self.stop = True
        if self._disconnect_evt and self.loop:
            self.loop.call_soon_threadsafe(self._disconnect_evt.set)
        try:
            self.ui.root.after(300, self.ui.root.destroy)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Einrichtung eines hinterlegten Geräts
# ---------------------------------------------------------------------------
async def do_enroll(enroll_code, name, password=None):
    async with aiohttp.ClientSession() as s:
        sig = Signal(s)
        payload = {"action": "enroll", "enrollCode": enroll_code, "name": name or device_label(), "os": os_label()}
        if password:
            payload["password"] = password
        res = await sig.call(payload)
        save_config({"device": res["device"], "token": res["token"], "name": res.get("name"), "pubId": res.get("pubId", "")})
        return res


async def set_password(password):
    cfg = load_config()
    if not cfg.get("device"):
        raise RuntimeError("nicht eingerichtet")
    async with aiohttp.ClientSession() as s:
        return await Signal(s).call({"action": "setpw", "device": cfg["device"], "token": cfg["token"], "password": password or ""})


async def set_mode(mode):
    cfg = load_config()
    if not cfg.get("device"):
        raise RuntimeError("nicht eingerichtet")
    async with aiohttp.ClientSession() as s:
        return await Signal(s).call({"action": "setmode", "device": cfg["device"], "token": cfg["token"], "mode": mode})


async def get_status():
    cfg = load_config()
    if not cfg.get("device"):
        raise RuntimeError("nicht eingerichtet")
    async with aiohttp.ClientSession() as s:
        return await Signal(s).call({"action": "status", "device": cfg["device"], "token": cfg["token"]})


def run_enroll(args):
    code = args.code
    if not code:
        try:
            code = input("Einrichtungs-Code (6 Stellen, aus dem Intranet): ").strip()
        except EOFError:
            code = ""
    code = "".join(ch for ch in (code or "") if ch.isdigit())[:6]
    if len(code) != 6:
        print("Kein gültiger 6-stelliger Code.")
        return 1
    try:
        res = asyncio.run(do_enroll(code, args.name, getattr(args, "pw", None)))
        print("Gerät eingerichtet:", res.get("name"))
        print("Dauerhaft starten:  --service")
        return 0
    except Exception as e:
        print("Einrichtung fehlgeschlagen:", e)
        return 1


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--service", action="store_true", help="hinterlegtes Gerät (unbeaufsichtigt)")
    ap.add_argument("--edition", choices=["quick", "full"], help="quick = Schnellhilfe, full = Vollversion (Host)")
    ap.add_argument("--enroll", action="store_true", help="Gerät einmalig einrichten")
    ap.add_argument("--code", help="Einrichtungs-Code (bei --enroll)")
    ap.add_argument("--pw", help="Zugriffs-Passwort (optional, bei --enroll)")
    ap.add_argument("--name", help="Anzeigename des Geräts")
    args, _ = ap.parse_known_args()

    if args.enroll:
        sys.exit(run_enroll(args))

    edition = args.edition or ("full" if args.service else "quick")
    mode = "quick" if edition == "quick" else "service"
    ui = UI(mode)

    # Vollversion: erst einrichten, falls noch nicht geschehen
    if mode == "service" and not (load_config().get("device") and load_config().get("token")):
        tmp = tk.Tk(); tmp.withdraw()
        try:
            from tkinter import simpledialog, messagebox
            messagebox.showinfo(APP_NAME, "Vollversion einrichten:\nBitte den 6-stelligen Einrichtungs-Code aus dem Intranet\n(Fernwartung → Gerät hinzufügen) eingeben.\n\nEin Zugriffs-Passwort brauchst du jetzt nicht – das stellst du\nnachher bequem im Programm ein (zufällig oder fest).")
            code = simpledialog.askstring(APP_NAME, "Einrichtungs-Code (6 Stellen):") or ""
            code = "".join(ch for ch in code if ch.isdigit())[:6]
        finally:
            tmp.destroy()
        if len(code) != 6:
            return
        try:
            asyncio.run(do_enroll(code, device_label(), None))
        except Exception as e:
            UI("quick").info(APP_NAME, "Einrichtung fehlgeschlagen: %s" % e)
            return

    agent = Agent(ui, mode)

    if mode == "quick":
        ui.show_main(agent.request_quit)
    else:
        cfg = load_config()
        ident = str(cfg.get("device", ""))[-9:].upper() or "–"

        def apply_random():
            """Zufälliges Passwort erzeugen, setzen und anzeigen (Modus = Passwort)."""
            pw = gen_password()
            try:
                asyncio.run(set_password(pw))
                update_config(pwstyle="random")
                agent.random_pw = pw
                ui.run_soon(lambda: (ui.set_host_mode("password", True), ui.set_pw_style("random"), ui.set_pw_value(pw)))
            except Exception as e:
                ui.info(APP_NAME, "Fehler: %s" % e)

        def set_fixed():
            pw = ui.ask_text(APP_NAME, "Festes Zugriffs-Passwort (mind. 4 Zeichen):", show="•")
            if not pw:
                return
            if len(pw) < 4:
                ui.info(APP_NAME, "Passwort zu kurz (mind. 4 Zeichen).")
                return
            try:
                asyncio.run(set_password(pw))
                update_config(pwstyle="fixed")
                agent.random_pw = None
                ui.run_soon(lambda: (ui.set_host_mode("password", True), ui.set_pw_style("fixed"), ui.set_pw_value("")))
                ui.info(APP_NAME, "Festes Passwort gespeichert.")
            except Exception as e:
                ui.info(APP_NAME, "Fehler: %s" % e)

        def on_pwstyle(style):
            if style == "random":
                apply_random()
            else:
                ui.run_soon(lambda: ui.set_pw_style("fixed"))
                set_fixed()

        def on_pwaction():
            if load_config().get("pwstyle", "random") == "fixed":
                set_fixed()
            else:
                apply_random()

        def change_mode(mode):
            if mode == "password":
                style = load_config().get("pwstyle") or "random"
                if style == "fixed":
                    try:
                        st = asyncio.run(get_status())
                    except Exception:
                        st = {}
                    if st.get("hasPw"):
                        try:
                            asyncio.run(set_mode("password"))
                        except Exception as e:
                            ui.info(APP_NAME, "Fehler: %s" % e); return
                        ui.run_soon(lambda: (ui.set_host_mode("password", True), ui.set_pw_style("fixed"), ui.set_pw_value("")))
                    else:
                        set_fixed()
                else:
                    apply_random()
                return
            try:
                r = asyncio.run(set_mode(mode))
                ui.run_soon(lambda m=r.get("unattended", mode), h=r.get("hasPw", False): ui.set_host_mode(m, h))
            except Exception as e:
                ui.info(APP_NAME, "Fehler: %s" % str(e))

        def open_intranet():
            try:
                import webbrowser
                webbrowser.open(BASE_URL + "/fernwartung")
            except Exception:
                pass

        ui.show_host(cfg.get("name") or device_label(), ident,
                     {"close": agent.request_quit, "open": open_intranet, "mode": change_mode,
                      "pwstyle": on_pwstyle, "pwaction": on_pwaction})

        def load_status():
            try:
                r = asyncio.run(get_status())
                mode = r.get("unattended", "ask"); has_pw = r.get("hasPw", False)
                style = load_config().get("pwstyle") or "random"
                pub = r.get("pubId", "")
                ui.run_soon(lambda: (ui.set_ident(pub) if pub else None,
                                     ui.set_host_mode(mode, has_pw),
                                     ui.set_pw_style(style),
                                     ui.set_last_access(r.get("lastAccess", 0), r.get("lastBy", ""))))
                # Zufalls-Passwort: beim Start frisch erzeugen, damit die Anzeige stimmt
                if mode == "password" and style == "random":
                    apply_random()
            except Exception:
                pass
        threading.Thread(target=load_status, daemon=True).start()

    def net_thread():
        try:
            asyncio.run(agent.run())
        except Exception as e:
            ui.run_soon(lambda: (ui.set_status("Fehler: %s" % e, RED, RED) if getattr(ui, "status_lbl", None) else None))

    threading.Thread(target=net_thread, daemon=True).start()
    try:
        ui.root.mainloop()
    except KeyboardInterrupt:
        pass
    agent.stop = True


if __name__ == "__main__":
    main()
