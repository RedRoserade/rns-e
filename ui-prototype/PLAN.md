# UI prototype — plan and status

The living document for this sub-project. **Start every session here**, and
update it at the end of one: tick what got done, log decisions, move the
"Next" pointer.

Goal: a head-unit UI for the RNS-E build that follows the look and UX of the
original Audi RNS-E (manual: `rns-e.pdf`), modernised, driven by the original
front panel, with Android Auto on the touch screen.

This is a **learning project first**. André builds parts himself; see
[Who builds what](#who-builds-what).

---

## Status

**Current milestone: M1 — shell + Setup menu on the desktop.**

Next up (André): make `tests/test_navigation.py` pass by implementing
`src/rnse_ui/navigation.py`. 6 tests fail on purpose. Two of the 5 passing ones
(`test_return_goes_up_one_level`, `test_home_returns_...`) pass only by
accident with the placeholder and become meaningful once corners work.

---

## Who builds what

| Area | Owner | Notes |
|---|---|---|
| Project scaffold, `__main__.py`, `ui_state.py` (Python↔QML bridge) | Claude | |
| `panel.py` — event vocabulary + keyboard harness | Claude | Names follow `../docs/keymap.json` |
| `qml/Frame.qml`, `qml/Theme.qml` — the shared chrome | Claude | Worked example of QML for André to read |
| `screens.py` — screen registry | shared | Add screens as they are built |
| **`navigation.py` — function / history / home / return / setup rules** | **André** | Spec in the module docstring and in the tests |
| **`qml/screens/setup_*.qml` — the Setup list screen** | **André** | First real screen; list + cursor on the arc |
| Radio screen, later screens | André, Claude reviews | |
| Display calibration (insets + touch) | TBD | Decide owner when M2a starts; see below |

Claude: don't write André's parts unless asked. Explain, review, hint,
write tests — fine.

---

## Milestones

### M1 — shell + Setup menu, desktop only, keyboard as panel
- [x] Stack chosen (see Decisions)
- [x] Scaffold: uv project, PySide6, QML loads, keyboard harness, `--screenshot`
- [x] Frame: title line, corner labels, panel, four arc halves that light per corner, tabs
- [x] Theme with per-function accent
- [x] Screen registry with real titles/corners from the manual
- [x] Navigation spec as tests
- [ ] **André:** `navigation.py` — all tests green
- [ ] **André:** Setup list screen (`qml/screens/setup_radio.qml` etc. — probably one
      shared `SetupList.qml` component loaded by thin per-screen files):
      rows, cursor dot riding the panel's left curve (`Frame.panelLeftAt(y)`),
      ▲▼ scroll arrows, value boxes (`▼ local`), `▷` for submenus (p. 27-29)
- [ ] Decide where list *data* (items, current values) lives — Python model vs QML
- [ ] Transitions: something tasteful when screens change (the "modern" part)

### M2 — on the Pi
- [ ] Pi OS Lite + PySide6 (pip wheels exist for aarch64), run with `-platform eglfs`, no desktop
- [ ] Real panel input: serial source from `../arduino/listener` emitting the same `PanelEvent`s
- [ ] Measure: startup time, idle CPU, frame rate of transitions
- [ ] Decide Pi 3B+ vs Pi 4 on the numbers

### M2a — display calibration (needed before the UI is usable in the car)
The touch digitiser was laminated off-centre: the left and right edges of the
picture are hidden, the right worse. The 800x480 `Frame` must fit the visible
area, and touch coordinates must line up with what is drawn. Both need
per-install configuration, so build a **calibration screen** first and let it
write the config.
- [ ] Config store: one small file (e.g. `~/.config/rnse-ui/display.json`) with
      `inset {left, top, right, bottom}` in screen pixels and the touch
      calibration; load at startup, expose to QML like `fullscreen`.
      `--inset L,T,R,B` overrides for quick tests.
- [ ] `Main.qml`: place the `Frame` in the inset rectangle instead of
      `centerIn`; scale-to-fit (uniform, `min(w/800, h/480)`, centred) so
      arcs stay circular and nothing is cropped. Real-pixel rule (decision 4)
      still holds *inside* the Frame.
- [ ] Calibration screen, reachable from Setup (and from a panel combo that
      works even when the UI is mis-set): border + tick marks, panel keys /
      knob nudge each edge in turn, ENTER saves, RETURN cancels.
- [ ] Touch calibration step: tap targets (corners + centre), fit an affine
      transform, show a crosshair at the touch point to verify. Check first
      whether libinput/eglfs calibration (`LIBINPUT_CALIBRATION_MATRIX` udev
      property, or `QT_QPA_EGLFS_*`) already does this below the app; if so
      the screen only writes that, otherwise apply the transform in the app.
      Touch must be mapped *after* the inset/scale so taps hit the Frame.
- [ ] Tests: pure-Python parts (config load/validate, affine fit) need no Qt.
- Alternatives considered, not chosen as the main route: kernel/DRM mode
  margins (`video=...margin_*`, ignored by some drivers; useful if a second
  app such as the Android Auto surface shares the screen), the display
  board's own H/V position menu (check if it has one — free to try), a plain
  smaller window size (a subset of insets).
- Open: how many pixels are lost per edge (measure with the calibration
  screen); is the Pi on eglfs/KMS (decides whether DRM margins are viable).

### M3 — Android Auto spike
- [ ] Build/run crankshaft-core on the Pi with a phone; stock crankshaft-ui-slim first
- [ ] Try our UI as a second crankshaft-core WebSocket client (see `docs/ANDROID_AUTO.md`)
- [ ] Choose integration: embedded (one app) vs two apps switched by a compositor

### M4 — Radio (RTL-SDR)
- [ ] rtl_fm / SoapySDR pipeline + RDS (redsea) as a background service
- [ ] Radio main screen (station list), Band, Tuning, Memory

### Later
CAN integration (illumination, ignition — see `../docs/CANBUS.md`), audio routing
(PipeWire), speller (p. 30-32), control wheel (p. 33), media, Car/Setup content.

---

## Decisions

Newest last. Don't delete — strike through and add a new entry if reversed.

1. **2026-10-03 — UI stack: Qt Quick (QML) + PySide6.** GPU-rendered, runs
   without a desktop (eglfs), Python backend in-process, declarative UI close
   to HTML/CSS. Long-lived (Qt is the automotive IVI default). Rejected:
   browser kiosk (Chromium RAM/boot cost on a Pi 3B+, can't embed AA video
   sensibly), Electron (same, worse), Tauri (WebKitGTK slow on Pi), Flutter
   (flutter-pi is community-maintained; Dart), React Native (no embedded
   Linux target).
2. **2026-10-03 — Separate uv project in `ui-prototype/`**, not part of the
   root `rnse` package, so the reverse-engineering tools stay dependency-light.
   `requires-python >= 3.11` to stay installable on Pi OS Bookworm.
3. **2026-10-03 — Panel is an event source, nothing more.** The UI consumes
   `PanelEvent`s; keyboard, serial and (later) uinput are interchangeable
   sources. Possible later step: publish panel input as a uinput device so
   Android Auto (which supports rotary input natively) gets the knob too.
4. **2026-10-03 — Real pixels.** QML is written at 800x480; desktop zoom via
   `QT_SCALE_FACTOR`, never by scaling the layout.
5. **2026-10-03 — Setup is a mode, not a function.** Matches the manual:
   "Setup Radio" keeps the radio's colour and SETUP toggles it.
6. **2026-10-03 — Navigation core is pure Python, no Qt**, so it is testable
   with plain pytest. `ui_state.py` adapts it to QML.
7. **2026-10-22 — Display fit via per-edge insets + scale-to-fit, set by an
   in-app calibration screen.** The digitiser hides the left/right edges
   unevenly, so width/height alone isn't enough; four insets are. Touch
   calibration lives in the same screen. See M2a.

Pending (André, while doing `navigation.py`):
- Corner pressed while in a corner submenu: stack or replace? Same corner again?
- Function button while in Setup: leave Setup, or switch function and stay in Setup?

---

## Open questions

- Accent colours for NAME, TEL, INFO, CAR are guesses (`Theme.qml`). Find
  screenshots in the manual or photos of a real unit.
- Font: the original uses an Audi typeface. Pick an open look-alike (candidates
  to try: Barlow, Saira Semi Condensed, Exo 2, DIN-alikes) and bundle it.
- crankshaft-core's video transports (`websocket-jpeg`, `webrtc`): which can a
  PySide6 client consume at acceptable CPU on a Pi? See `docs/ANDROID_AUTO.md`.
- GPL-3.0 (crankshaft) vs Apache-2.0 (this repo): talking to crankshaft-core
  over its WebSocket as a separate process should keep our code independent,
  but confirm before linking or copying any of its code.

---

## Session log

One line per session: date — what happened — where it stopped.

- 2026-10-03 — Stack chosen; scaffold, Frame, Theme, registry, tests, docs.
  Researched crankshaft-core/ui-slim. Stopped at: André to implement
  `navigation.py`.
- 2026-10-22 — Planned display calibration (M2a): insets, scale-to-fit, touch
  calibration screen. No code yet. Stopped at: unchanged (André on
  `navigation.py`); M2a needs an owner decision when it starts.
