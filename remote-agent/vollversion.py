# Einstieg: Vollversion (Host) – hinterlegtes Geraet fuer eingehende Verbindungen.
import sys
if "--edition" not in sys.argv:
    sys.argv += ["--edition", "full"]
import agent
if __name__ == "__main__":
    agent.main()
