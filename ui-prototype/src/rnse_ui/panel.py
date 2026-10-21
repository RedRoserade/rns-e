"""
The front panel as the UI sees it: a small vocabulary of input events.

Event names follow ../../docs/keymap.json (the map produced from the real
panel), so the serial source can pass keymap names straight through. The UI
never cares where an event came from — the desktop keyboard harness here, the
Arduino listener over USB serial later, or a uinput device after that.
"""

from enum import StrEnum

from PySide6.QtCore import QEvent, QObject, Qt, Signal


class PanelEvent(StrEnum):
    # Function buttons, along the bottom of the panel
    RADIO = "radio"
    MEDIA = "cd_tv_sd_media"
    NAME = "name"
    TEL = "tel"
    NAV = "nav"
    INFO = "info"
    CAR = "car"
    SETUP = "setup"

    # The four control buttons around the knob, one per screen corner
    TOP_LEFT = "top_left_quad"
    TOP_RIGHT = "top_right_quad"
    BOTTOM_LEFT = "bottom_left_quad"
    BOTTOM_RIGHT = "bottom_right_quad"

    RETURN = "return"
    PREV = "back"  # |<< — keymap calls it "back"; not to be confused with RETURN
    NEXT = "fwd"   # >>|
    EJECT = "eject"
    FLIP_SCREEN = "flip_screen"

    # Control knob (keymap: scroll_wheel + scroll_click)
    KNOB_CW = "scroll_wheel_cw"
    KNOB_CCW = "scroll_wheel_ccw"
    KNOB_PRESS = "scroll_click"

    # Volume knob (keymap: volume_knob). Its push (power/mute) is not on the
    # serial bus at all — see PROTOCOL.md — so there is no event for it here.
    VOLUME_UP = "volume_knob_cw"
    VOLUME_DOWN = "volume_knob_ccw"


FUNCTION_BUTTONS = (
    PanelEvent.RADIO, PanelEvent.MEDIA, PanelEvent.NAME, PanelEvent.TEL,
    PanelEvent.NAV, PanelEvent.INFO, PanelEvent.CAR, PanelEvent.SETUP,
)

# Corner buttons in the order the UI indexes corners: TL, TR, BL, BR.
CORNER_BUTTONS = (
    PanelEvent.TOP_LEFT, PanelEvent.TOP_RIGHT,
    PanelEvent.BOTTOM_LEFT, PanelEvent.BOTTOM_RIGHT,
)

# Desktop stand-in for the panel. Keep README.md's key table in sync.
KEYBOARD_MAP: dict[Qt.Key, PanelEvent] = {
    Qt.Key.Key_F1: PanelEvent.RADIO,
    Qt.Key.Key_F2: PanelEvent.MEDIA,
    Qt.Key.Key_F3: PanelEvent.NAME,
    Qt.Key.Key_F4: PanelEvent.TEL,
    Qt.Key.Key_F5: PanelEvent.NAV,
    Qt.Key.Key_F6: PanelEvent.INFO,
    Qt.Key.Key_F7: PanelEvent.CAR,
    Qt.Key.Key_F8: PanelEvent.SETUP,
    # Q/E/Z/C sit at the corners of the left hand, like the buttons round the knob
    Qt.Key.Key_Q: PanelEvent.TOP_LEFT,
    Qt.Key.Key_E: PanelEvent.TOP_RIGHT,
    Qt.Key.Key_Z: PanelEvent.BOTTOM_LEFT,
    Qt.Key.Key_C: PanelEvent.BOTTOM_RIGHT,
    Qt.Key.Key_Backspace: PanelEvent.RETURN,
    Qt.Key.Key_Escape: PanelEvent.RETURN,
    Qt.Key.Key_BracketLeft: PanelEvent.PREV,
    Qt.Key.Key_BracketRight: PanelEvent.NEXT,
    Qt.Key.Key_Down: PanelEvent.KNOB_CW,
    Qt.Key.Key_Up: PanelEvent.KNOB_CCW,
    Qt.Key.Key_Return: PanelEvent.KNOB_PRESS,
    Qt.Key.Key_Enter: PanelEvent.KNOB_PRESS,
    Qt.Key.Key_Space: PanelEvent.KNOB_PRESS,
    Qt.Key.Key_Plus: PanelEvent.VOLUME_UP,
    Qt.Key.Key_Equal: PanelEvent.VOLUME_UP,
    Qt.Key.Key_Minus: PanelEvent.VOLUME_DOWN,
}

# Events that may auto-repeat when a key is held. Buttons on the real panel
# report press/release, not repeats, so only the encoders get them.
_REPEATABLE = {
    PanelEvent.KNOB_CW, PanelEvent.KNOB_CCW,
    PanelEvent.VOLUME_UP, PanelEvent.VOLUME_DOWN,
}


class KeyboardPanel(QObject):
    """Turns desktop key presses and the mouse wheel into panel events.

    Install it as an application-wide event filter. It swallows only the keys
    it maps, so text input elsewhere keeps working.
    """

    event = Signal(str)  # a PanelEvent value

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:
        if ev.type() == QEvent.Type.KeyPress:
            mapped = KEYBOARD_MAP.get(Qt.Key(ev.key()))
            if mapped is None:
                return False
            if not ev.isAutoRepeat() or mapped in _REPEATABLE:
                self.event.emit(mapped.value)
            return True
        if ev.type() == QEvent.Type.Wheel:
            # Both the window and the item under the cursor see the wheel event;
            # only react once.
            if not obj.isWindowType():
                return False
            dy = ev.angleDelta().y()
            if dy:
                self.event.emit((PanelEvent.KNOB_CCW if dy > 0 else PanelEvent.KNOB_CW).value)
            return True
        return False
