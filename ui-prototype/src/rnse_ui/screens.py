"""
Screen registry: what exists, what each screen is called, what its corners do.

Pure data, no Qt. Page numbers are the manual's printed page numbers (see
docs/DESIGN.md for how they map to PDF pages).

A screen's QML lives in qml/screens/<id>.qml; screens without one render
qml/screens/Placeholder.qml, so a screen can be registered here long before it
is drawn.
"""

from dataclasses import dataclass

from .panel import PanelEvent


@dataclass(frozen=True)
class Corner:
    label: str
    target: str | None = None  # screen id the corner button opens; None = not wired


NO_CORNER = None
Corners = tuple[Corner | None, Corner | None, Corner | None, Corner | None]  # TL, TR, BL, BR


@dataclass(frozen=True)
class Screen:
    id: str
    title: str          # title line, centred at the top
    subtitle: str = ""  # submenu line inside the panel, e.g. "Destination" (p. 28)
    corners: Corners = (None, None, None, None)


def _family(root: Screen, *children: tuple[str, str]) -> list[Screen]:
    """A root plus the submenus its corners open.

    Corner submenus keep the root's title and corners — the manual shows the
    same four labels with the active one lit (p. 57, fig. 54).
    """
    return [root] + [
        Screen(id=sid, title=root.title, subtitle=subtitle, corners=root.corners)
        for sid, subtitle in children
    ]
  

# Radio, p. 56
_RADIO = Screen(
    "radio", "Radio FM",
    corners=(Corner("Memory", "radio_memory"), Corner("Band", "radio_band"),
             Corner("Tuning", "radio_tuning"), Corner("Sound", "radio_sound")),
)

# MP3 / media, p. 33 fig. 29
_MEDIA = Screen(
    "media", "Media",
    corners=(Corner("MP3 list", "media_list"), Corner("Source", "media_source"),
             Corner("MP3 ctrl", "media_ctrl"), Corner("Sound", "media_sound")),
)

# Navigation, p. 27 fig. 20
_NAV = Screen(
    "nav", "Navigation",
    corners=(Corner("Memory", "nav_memory"), Corner("Route", "nav_route"),
             Corner("Nav-Info", "nav_info"), Corner("Map", "nav_map")),
)

# Setup submenus are the same whichever function Setup was opened from (p. 169)
_SETUP_CORNERS: Corners = (
    NO_CORNER, Corner("Settings", "setup_settings"),
    Corner("Display", "setup_display"), Corner("Sound", "setup_sound"),
)


def _setup(function_id: str, name: str) -> Screen:
    return Screen(f"setup_{function_id}", f"Setup {name}", corners=_SETUP_CORNERS)


_ALL: list[Screen] = [
    *_family(_RADIO, ("radio_memory", "Memory"), ("radio_band", "Band"),
             ("radio_tuning", "Tuning"), ("radio_sound", "Sound")),
    *_family(_MEDIA, ("media_list", "MP3 list"), ("media_source", "Source"),
             ("media_ctrl", "MP3 ctrl"), ("media_sound", "Sound")),
    *_family(_NAV, ("nav_memory", "Memory"), ("nav_route", "Route"),
             ("nav_info", "Nav-Info"), ("nav_map", "Map")),
    Screen("name", "Directory"),
    Screen("tel", "Telephone"),
    Screen("info", "Information"),
    Screen("car", "Car"),
    _setup("radio", "Radio"),
    _setup("media", "Media"),
    _setup("nav", "Navigation"),
    _setup("name", "Directory"),
    _setup("tel", "Telephone"),
    _setup("info", "Information"),
    _setup("car", "Car"),
    Screen("setup_settings", "Setup", "Settings", _SETUP_CORNERS),
    Screen("setup_display", "Setup", "Display", _SETUP_CORNERS),
    Screen("setup_sound", "Setup", "Sound", _SETUP_CORNERS),
]

SCREENS: dict[str, Screen] = {s.id: s for s in _ALL}

# Function button -> its main menu. SETUP is deliberately absent: it is not a
# function of its own but a mode on top of the current one (p. 16, p. 169).
ROOTS: dict[PanelEvent, str] = {
    PanelEvent.RADIO: "radio",
    PanelEvent.MEDIA: "media",
    PanelEvent.NAME: "name",
    PanelEvent.TEL: "tel",
    PanelEvent.NAV: "nav",
    PanelEvent.INFO: "info",
    PanelEvent.CAR: "car",
}

# Function -> the Setup main menu SETUP opens from it.
SETUP_ROOTS: dict[PanelEvent, str] = {f: f"setup_{sid}" for f, sid in ROOTS.items()}
