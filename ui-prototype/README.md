# rnse-ui — head-unit UI prototype

A UI in the style of the Audi RNS-E for the RNS-E project: Qt Quick (QML)
for the screen, Python (PySide6) behind it. Runs on the desktop now, and is
meant for an 800x480 screen on a Raspberry Pi.

Plan, status and decisions: [`PLAN.md`](PLAN.md). Design reference:
[`docs/DESIGN.md`](docs/DESIGN.md) and `rns-e.pdf`.

## Run

Needs [uv](https://docs.astral.sh/uv/).

```sh
cd ui-prototype
uv run rnse-ui                          # 800x480 window
QT_SCALE_FACTOR=2 uv run rnse-ui        # same, zoomed on a big monitor
uv run rnse-ui --fullscreen             # in the car
uv run pytest -q                        # tests
```

Render a PNG without opening a window (handy for checking changes):

```sh
QT_QPA_PLATFORM=offscreen uv run rnse-ui --play nav,top_right_quad --screenshot out.png
```

## Keyboard = front panel

| Panel | Key |
|---|---|
| FM/AM · CD/SD · NAME · TEL · NAV · INFO · CAR · SETUP | F1 … F8 |
| Control buttons TL · TR · BL · BR | Q · E · Z · C |
| Control knob rotate | ↑ / ↓ or mouse wheel |
| Control knob press | Enter or Space |
| RETURN | Backspace or Esc |
| \|<< · >>\| | [ · ] |
| Volume | + / − |

Defined in `src/rnse_ui/panel.py` (`KEYBOARD_MAP`).

## Where things are

| Path | What |
|---|---|
| `src/rnse_ui/panel.py` | Panel events (named after `../docs/keymap.json`) and the keyboard stand-in |
| `src/rnse_ui/screens.py` | Every screen: title, subtitle, corner labels and targets |
| `src/rnse_ui/navigation.py` | Navigation rules — function / history / home / return / setup |
| `src/rnse_ui/ui_state.py` | What QML sees as `ui` |
| `src/rnse_ui/qml/Frame.qml` | The shared chrome: title, corners, panel, arcs |
| `src/rnse_ui/qml/Theme.qml` | Colours, fonts, sizes |
| `src/rnse_ui/qml/screens/` | One QML file per screen id; `Placeholder.qml` otherwise |

### Adding a screen

1. Register it in `screens.py` (and wire a corner's `target` to it).
2. Create `qml/screens/<id>.qml`. Its root fills the panel; listen to the knob
   with `Connections { target: ui; function onKnobRotated(delta) {…} }`
   (see `Placeholder.qml`), and import `".."` for `Theme`.

`prototype.html` is the earlier HTML sketch, kept for reference.
