# Gemeinsamer Absturz-Schutz für die Einstiegsprogramme.
# Fängt JEDEN Fehler beim Start (auch beim Laden der Bibliotheken) ab,
# schreibt ihn in eine Log-Datei und zeigt ein sichtbares Fenster –
# damit nichts mehr „kommentarlos" abstürzt.
import os
import sys
import traceback


def _log_path():
    base = os.path.expanduser("~")
    try:
        if sys.platform == "darwin":
            d = os.path.join(base, "Library", "Logs")
            if os.path.isdir(d):
                return os.path.join(d, "AlexReviewit-Fernwartung.log")
    except Exception:
        pass
    return os.path.join(base, "AlexReviewit-Fernwartung-Fehler.log")


def _show(title, text):
    """Zeigt eine native Meldung – ganz ohne weitere Bibliotheken."""
    short = text if len(text) <= 1400 else text[:1400] + " …"
    try:
        if sys.platform == "darwin":
            import subprocess
            msg = short.replace("\\", "\\\\").replace('"', "'").replace("\n", "\\n")
            subprocess.run(["osascript", "-e",
                            'display dialog "%s" with title "%s" buttons {"OK"} with icon stop' % (msg, title)],
                           check=False)
            return
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, short, title, 0x10)
            return
    except Exception:
        pass
    try:
        sys.stderr.write(title + "\n" + text + "\n")
    except Exception:
        pass


def run(main_callable):
    """Führt das Programm aus und meldet Startfehler verständlich."""
    try:
        main_callable()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 – wir wollen wirklich alles abfangen
        tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        path = _log_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            path = "(konnte nicht gespeichert werden)"
        summary = "%s: %s" % (type(e).__name__, e)
        _show("Alex Reviewit Fernwartung – Fehler beim Start",
              "Das Programm konnte nicht starten.\n\n%s\n\nDetails wurden gespeichert in:\n%s\n\n"
              "Bitte diese Datei an die IT senden." % (summary, path))
        sys.exit(1)
