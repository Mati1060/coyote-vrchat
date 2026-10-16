"""Coyote x VRChat - entry point.

Usage:
  python main.py                opens the window
  python main.py --simulate     opens the window with a FAKE Coyote (to try the interface without the device)
  python main.py --connect      tries to connect to the Coyote right away
  python main.py --headless     no window (OSC + AI API only); Ctrl+C to quit
  python main.py --settings C:\\path\\settings.json   use a different settings file
"""
import argparse
import sys
import time


def _enable_hidpi():
    """On Windows, avoids a blurry window on displays scaled to 125%/150%."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main(argv=None) -> int:
    if sys.version_info < (3, 10):
        print("This program needs Python 3.10 or newer (you have %d.%d)." % sys.version_info[:2])
        return 2

    ap = argparse.ArgumentParser(description="DG-LAB Coyote 3.0 control from VRChat OSC")
    ap.add_argument("--simulate", action="store_true", help="use a simulated Coyote (no Bluetooth)")
    ap.add_argument("--connect", action="store_true", help="connect on startup")
    ap.add_argument("--headless", action="store_true", help="no window")
    ap.add_argument("--settings", default=None, help="path to settings.json")
    args = ap.parse_args(argv)

    from coyote_vrc.ble import SimulatedTransport
    from coyote_vrc.engine import Engine

    engine = Engine(settings_path=args.settings, transport=SimulatedTransport() if args.simulate else None)
    if args.simulate:
        engine.control.log("SIMULATED MODE: no real device is being used")
    engine.start()
    if args.connect:
        engine.connect()

    if args.headless:
        print("Running without a window. Ctrl+C to quit.")
        try:
            while True:
                time.sleep(5)
                link = engine.link.status()
                osc = engine.osc_status()
                print(f"[bluetooth: {link['state']}] [osc: {osc['packets']} packets] "
                      f"[intensity A/B: {engine.control.snapshot()['channels']['A']['output']:.0f}"
                      f"/{engine.control.snapshot()['channels']['B']['output']:.0f}]")
        except KeyboardInterrupt:
            pass
        finally:
            engine.shutdown()
        return 0

    try:
        from coyote_vrc.gui import App
    except ImportError as exc:
        engine.shutdown()
        print("Could not open the window (tkinter missing?):", exc)
        print("On Windows, reinstall Python with the 'tcl/tk and IDLE' option checked, or use --headless.")
        return 1

    _enable_hidpi()
    app = App(engine)
    try:
        app.mainloop()
    finally:
        engine.shutdown()  # idempotent: does nothing if the window already shut it down
    return 0


if __name__ == "__main__":
    sys.exit(main())
