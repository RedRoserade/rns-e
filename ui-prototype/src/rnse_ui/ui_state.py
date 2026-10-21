"""
The bridge between the Python side and QML.

QML only ever sees this object (as the `ui` context property). It routes
panel events: navigation ones to the Navigator, the knob straight through to
whichever screen is showing (screens own their own cursor), and exposes the
result as read-only properties QML can bind to.
"""

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from .navigation import Navigator
from .panel import PanelEvent

SCREENS_DIR = Path(__file__).parent / "qml" / "screens"

# Events that are none of the Navigator's business.
_KNOB = {PanelEvent.KNOB_CW: 1, PanelEvent.KNOB_CCW: -1}


class UiState(QObject):
    changed = Signal()

    # For the current screen's QML to consume. +1 = clockwise = down the list.
    knobRotated = Signal(int)
    knobPressed = Signal()
    # Everything else not handled here (|<< >>|, volume, eject...), for whoever
    # wants it. Carries the PanelEvent value.
    unhandled = Signal(str)

    def __init__(self, navigator: Navigator | None = None) -> None:
        super().__init__()
        self._nav = navigator or Navigator()

    @Slot(str)
    def dispatch(self, value: str) -> None:
        event = PanelEvent(value)
        if event in _KNOB:
            self.knobRotated.emit(_KNOB[event])
        elif event is PanelEvent.KNOB_PRESS:
            self.knobPressed.emit()
        else:
            before = (self._nav.function, self._nav.screen, self._nav.active_corner)
            self._nav.handle(event)
            after = (self._nav.function, self._nav.screen, self._nav.active_corner)
            if after != before:
                self.changed.emit()
            else:
                self.unhandled.emit(value)

    # Read by Theme.qml to pick the accent colour; Setup keeps its function's.
    @Property(str, notify=changed)
    def function(self) -> str:
        return self._nav.function.value

    @Property(str, notify=changed)
    def screenId(self) -> str:
        return self._nav.screen.id

    @Property(str, notify=changed)
    def title(self) -> str:
        return self._nav.screen.title

    @Property(str, notify=changed)
    def subtitle(self) -> str:
        return self._nav.screen.subtitle

    @Property("QVariantList", notify=changed)
    def corners(self) -> list[str]:
        """Corner labels TL, TR, BL, BR; "" where a corner is unused."""
        return [c.label if c else "" for c in self._nav.screen.corners]

    @Property(int, notify=changed)
    def activeCorner(self) -> int:
        """-1 when no corner is active."""
        corner = self._nav.active_corner
        return -1 if corner is None else corner

    @Property(QUrl, notify=changed)
    def screenSource(self) -> QUrl:
        qml = SCREENS_DIR / f"{self._nav.screen.id}.qml"
        if not qml.exists():
            qml = SCREENS_DIR / "Placeholder.qml"
        return QUrl.fromLocalFile(str(qml))
