"""
Development helper: run the UI and restart it whenever a QML file changes.

    uv run rnse-ui-watch                 # same flags as rnse-ui are passed through
    uv run rnse-ui-watch --fullscreen

Closing the window (clean exit) ends the watcher too. If the UI crashes — a
QML syntax error, say — the watcher waits for the next change and tries again.
Plain polling of modification times: no extra dependency, fine for a few files.
"""

import subprocess
import sys
import time
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"
WATCHED_SUFFIXES = {".qml", ".js", ".mjs"}
WATCHED_NAMES = {"qmldir"}
POLL_S = 0.25
SETTLE_S = 0.15  # editors often write several files in a burst


def snapshot(root: Path = QML_DIR) -> dict[Path, int]:
    """Modification time (ns) of every watched file under `root`."""
    return {
        p: p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file() and (p.suffix in WATCHED_SUFFIXES or p.name in WATCHED_NAMES)
    }


def _stop(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def _start() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-m", "rnse_ui", *sys.argv[1:]])


def main() -> int:
    seen = snapshot()
    child = _start()
    try:
        while True:
            time.sleep(POLL_S)
            now = snapshot()
            if now != seen:
                time.sleep(SETTLE_S)
                now = snapshot()
                changed = sorted(
                    p.relative_to(QML_DIR).as_posix()
                    for p in now.keys() | seen.keys()
                    if now.get(p) != seen.get(p)
                )
                seen = now
                print(f"[watch] restarting ({', '.join(changed)})", flush=True)
                _stop(child)
                child = _start()
            elif child.poll() == 0:
                return 0  # window closed on purpose
            elif child.poll() is not None:
                print(f"[watch] exited with {child.returncode}; waiting for a change", flush=True)
                while snapshot() == seen:
                    time.sleep(POLL_S)
                seen = snapshot()
                child = _start()
    except KeyboardInterrupt:
        return 0
    finally:
        _stop(child)


if __name__ == "__main__":
    sys.exit(main())
