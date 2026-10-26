"""
Where the user is: which function, which screen, how they got there.

    >>> ANDRÉ'S FILE <<<  (see ../../PLAN.md, "Who builds what")

This is the heart of how the RNS-E *feels*. It is pure Python — no Qt — so it
can be driven and tested from tests/test_navigation.py without a window.

What is here now is a deliberately naive placeholder, just enough for the
app to run: function buttons switch function and always land on that
function's main menu. Nothing else is handled. The rules to implement, from
the manual (printed page numbers):

  * Control buttons (corners) open the submenu named by the current screen's
    Corner.target. A corner with no Corner, or a target of None, does nothing.
    The corner that led to the current screen is `active_corner` (p. 18:
    "the activated control button is illuminated and the corresponding corner
    of the screen is highlighted").
  * RETURN goes back one level within the function. At the main menu it does
    nothing (p. 18).
  * History: switching to another function remembers where you were; coming
    back restores it, sublevels included (p. 20, "History function").
  * Home: pressing the button of the function you are already in goes to its
    main menu (p. 20, "Home function").
  * SETUP opens the current function's Setup main menu (screens.SETUP_ROOTS).
    Pressing SETUP again leaves it, back to where you were (p. 16). Setup
    menus are *not* kept in the history (p. 20).

Decisions the manual leaves to you — write down what you chose in PLAN.md:

  * In a corner submenu, does pressing a different corner stack a new level
    or replace the current one? What does pressing the same corner again do?
  * Pressing a function button while in Setup: leave Setup and switch, or
    switch and stay in Setup?

The knob, |<< >>| and volume are not navigation; they never reach this class.
"""

from .panel import PanelEvent, CORNER_BUTTONS
from .screens import ROOTS, SCREENS, Screen


class Navigator:
    def __init__(self, start: PanelEvent = PanelEvent.RADIO) -> None:
        self.function: PanelEvent = start
        self._screen_id: str = ROOTS[start]
        self._active_corners: dict[str, int] = {}
        """The active corner of each screen"""

    @property
    def screen(self) -> Screen:
        screen = SCREENS[self._screen_id]

        active_corner = self._active_corners.get(self._screen_id)

        if active_corner is None:
            return screen

        corner = screen.corners[active_corner]

        if corner is None or corner.target is None:
            print(f"screen {self._screen_id} has no corner {active_corner}")
            return screen

        return SCREENS[corner.target]

    def _handle_corner(self, event: PanelEvent) -> None:
        match event:
            case PanelEvent.TOP_LEFT:
                corner_idx = 0
            case PanelEvent.TOP_RIGHT:
                corner_idx = 1
            case PanelEvent.BOTTOM_LEFT:
                corner_idx = 2
            case PanelEvent.BOTTOM_RIGHT:
                corner_idx = 3
            case _:
                return

        corner = self.screen.corners[corner_idx]

        if corner is None or corner.target is None:
            return

        self._active_corners[self._screen_id] = corner_idx
              

    @property
    def active_corner(self) -> int | None:
        """Index (TL=0, TR=1, BL=2, BR=3) of the corner that opened the
        current screen, or None at a main menu."""
        return self._active_corners.get(self._screen_id)

    def handle(self, event: PanelEvent) -> None:
        if event in ROOTS:
            # Pressing the function button with the function already active returns
            # to the root of that function
            if event is self.function:
                self._active_corners.pop(self._screen_id, None)
            
            self.function = event
            self._screen_id = ROOTS[event]

        if event in CORNER_BUTTONS:
            self._handle_corner(event)

        if event is PanelEvent.RETURN:
            self._active_corners.pop(self._screen_id, None)
