"""
The RNS-E's navigation rules, as tests. Most of these FAIL until
src/rnse_ui/navigation.py is implemented — that is the exercise.

    uv run pytest -v

Feel free to change, add or delete tests: they are a starting spec, not a
contract. Page numbers are the manual's printed ones.
"""

from rnse_ui.navigation import Navigator
from rnse_ui.panel import PanelEvent as E


def press(nav: Navigator, *events: E) -> Navigator:
    for event in events:
        nav.handle(event)
    return nav


# --- already passing with the placeholder ---------------------------------

def test_starts_on_radio_main_menu():
    nav = Navigator()
    assert nav.function is E.RADIO
    assert nav.screen.id == "radio"
    assert nav.active_corner is None


def test_function_button_switches_to_that_function():
    nav = press(Navigator(), E.NAV)
    assert nav.function is E.NAV
    assert nav.screen.id == "nav"


# --- control buttons and RETURN (p. 17-18) --------------------------------

def test_corner_opens_its_submenu():
    nav = press(Navigator(), E.TOP_RIGHT)  # Radio: "Band"
    assert nav.screen.id == "radio_band"
    assert nav.active_corner == 1


def test_corner_without_target_does_nothing():
    nav = press(Navigator(), E.SETUP, E.TOP_LEFT)  # Setup has no TL corner
    assert nav.screen.id == "setup_radio"


def test_return_goes_up_one_level():
    nav = press(Navigator(), E.TOP_RIGHT, E.RETURN)
    assert nav.screen.id == "radio"
    assert nav.active_corner is None


def test_return_at_main_menu_does_nothing():
    nav = press(Navigator(), E.RETURN)
    assert nav.function is E.RADIO
    assert nav.screen.id == "radio"


# --- history and home (p. 20) ----------------------------------------------

def test_history_restores_previous_screen_of_a_function():
    # The manual's own example: Tuning, then NAV, then FM/AM lands on Tuning.
    nav = press(Navigator(), E.BOTTOM_LEFT, E.NAV, E.RADIO)
    assert nav.screen.id == "radio_tuning"


def test_home_returns_to_main_menu_of_current_function():
    nav = press(Navigator(), E.BOTTOM_LEFT, E.RADIO)
    assert nav.screen.id == "radio"


# --- setup (p. 16, p. 169) -------------------------------------------------

def test_setup_opens_setup_of_current_function():
    nav = press(Navigator(), E.NAV, E.SETUP)
    assert nav.function is E.NAV  # Setup is a mode, the function stays
    assert nav.screen.id == "setup_nav"
    assert nav.screen.title == "Setup Navigation"


def test_setup_again_leaves_setup_to_where_you_were():
    nav = press(Navigator(), E.TOP_RIGHT, E.SETUP, E.SETUP)
    assert nav.screen.id == "radio_band"


def test_setup_is_not_remembered_in_history():
    nav = press(Navigator(), E.TOP_RIGHT, E.SETUP, E.NAV, E.RADIO)
    assert nav.screen.id == "radio_band"
