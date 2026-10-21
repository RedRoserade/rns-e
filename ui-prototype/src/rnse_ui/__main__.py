"""
Entry point.

    uv run rnse-ui               # 800x480 window, keyboard stands in for the panel
    uv run rnse-ui --fullscreen  # on the car's screen

    uv run rnse-ui --play nav,top_right_quad --screenshot out.png
                                 # replay panel events, save a PNG, quit

Zoom the desktop window with QT_SCALE_FACTOR=1.5 (or 2) — the QML is written
in real 800x480 pixels and should stay that way.
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from .panel import KeyboardPanel, PanelEvent
from .ui_state import UiState

QML_DIR = Path(__file__).parent / "qml"


def main() -> int:
    parser = argparse.ArgumentParser(prog="rnse-ui")
    parser.add_argument("--fullscreen", action="store_true",
                        help="fill the screen and hide the cursor (for the car)")
    parser.add_argument("--play", metavar="EVENTS", default="",
                        help="comma-separated panel events (PanelEvent values) to send at startup")
    parser.add_argument("--screenshot", metavar="PNG",
                        help="save the window to PNG after --play, then quit")
    args, qt_args = parser.parse_known_args()

    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setApplicationName("rnse-ui")

    ui = UiState()
    panel = KeyboardPanel()
    panel.event.connect(ui.dispatch)
    app.installEventFilter(panel)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("ui", ui)
    engine.rootContext().setContextProperty("fullscreen", args.fullscreen)
    engine.load(QML_DIR / "Main.qml")
    if not engine.rootObjects():
        return 1

    for event in filter(None, args.play.split(",")):
        ui.dispatch(PanelEvent(event.strip()).value)
    if args.screenshot:
        window: QQuickWindow = engine.rootObjects()[0]

        def shoot() -> None:
            try:
                window.grabWindow().save(args.screenshot)
            finally:
                app.quit()

        # Give the scene graph a moment to render and animations to settle.
        QTimer.singleShot(600, shoot)

    code = app.exec()
    # Tear QML down before `ui` goes, or bindings fire against a dead object.
    del engine
    return code


if __name__ == "__main__":
    sys.exit(main())
