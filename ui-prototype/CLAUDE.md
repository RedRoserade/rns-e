# ui-prototype — notes for Claude

A Qt Quick + PySide6 head-unit UI styled after the Audi RNS-E. Separate uv
project from the repo root.

**Read `PLAN.md` first** — status, decisions, who builds what, next step.
Update its Status, checkboxes, Decisions and Session log before a session ends.

## Ground rules

- **Learning project.** André writes `navigation.py` and the screen QML marked
  as his in `PLAN.md`. Don't implement those unless he asks; explain, review,
  hint, add tests instead.
- Visual and behavioural reference is `rns-e.pdf`. Its printed page numbers
  differ from PDF page numbers (PDF ≈ printed + 11…14, it has divider pages);
  cite printed numbers, as `docs/DESIGN.md` does.
- QML is in real 800x480 pixels. Colours and sizes come from `Theme.qml`.

## Run, test, look

```sh
uv run rnse-ui                         # window; keyboard = panel (see README)
uv run pytest -q

# Render without a display — use this to check visual changes yourself:
QT_QPA_PLATFORM=offscreen timeout 30 .venv/bin/rnse-ui \
    --play nav,top_right_quad --screenshot /path/to/out.png
```

Use `.venv/bin/rnse-ui` with `timeout` for screenshots; without
`QT_QPA_PLATFORM=offscreen` a real window opens on André's desktop. Event
names for `--play` are `PanelEvent` values in `src/rnse_ui/panel.py`.

## Layout

```
src/rnse_ui/
  __main__.py     entry point, CLI flags
  panel.py        PanelEvent vocabulary + desktop keyboard harness
  screens.py      screen registry (titles, corners) — pure data
  navigation.py   navigation rules — pure Python (André's)
  ui_state.py     QObject bridge exposed to QML as `ui`
  qml/
    Main.qml      window; Frame + Loader for the current screen
    Frame.qml     shared chrome: title, corners, panel, arcs
    Theme.qml     singleton (registered in qmldir)
    screens/      <screen id>.qml, else Placeholder.qml
tests/            pytest, no Qt needed
docs/
  DESIGN.md       visual + behaviour spec extracted from the manual
  ANDROID_AUTO.md crankshaft-core findings and integration options
```

## Gotchas met so far

- QML property names `right`, `left`, `top`, `bottom` clash with Item's FINAL
  anchor-line properties — "Cannot override FINAL property".
- A delegate with a `required property` gets no implicit `index`/model roles.
- Import `PySide6.QtQuick` before calling `grabWindow()` on the root object,
  or it arrives typed as a plain `QWindow`.
- Delete the `QQmlApplicationEngine` before context-property objects die, or
  shutdown spews "Cannot read property … of null".
