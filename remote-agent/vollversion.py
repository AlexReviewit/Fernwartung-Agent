# Einstieg: Vollversion (Host) – hinterlegtes Geraet fuer eingehende Verbindungen.
import sys
import _startguard

if "--edition" not in sys.argv:
    sys.argv += ["--edition", "full"]


def _start():
    import agent
    agent.main()


if __name__ == "__main__":
    _startguard.run(_start)
