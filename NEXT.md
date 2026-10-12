# Next steps

Where the bench work stopped on 2026-10-12, and what to do next. Findings are
in the docs; this file is the to-do list. Delete items as they are done.

## Where things stand

- **The panel can be driven without a head unit.** Input (keys, both
  rotaries), the link layer and the init sequence (`PROTOCOL.md` §4–§7), and
  now the lighting (§8): lamp frame `0x07` switches the button backlight
  (`0x40`), the four corner indicators and the daughter board; dimmer frame
  `0x06` sets brightness (C backlight, B corners). `arduino/listener` does all
  of it; LED rail on pin 9 from a PP3.
- **Head unit / CAN: parked.** Not needed to drive the panel. CAN (`0x635`
  dimming, ignition, etc.) will be handled in software by the UI later
  (`ui-prototype/`). `CANBUS.md` and `FIRMWARE.md` §5.3, §5.7 stay as
  reference.

## 1. Flash and check the refined listener

The lighting commands changed (2026-10-12). Not yet run on the panel.

- [ ] Flash `arduino/listener`. After `r`, expect `# init done`, then a
      dimmer frame and `lamps on=0x40` — backlight on at full by default.
- [ ] `b` toggles the backlight; `+`/`-` step brightness (B and C together,
      doubling/halving the on-time, 9 = full, 0 = off).
- [ ] `L 44` = backlight + NE; `L 44 4` = the same with NE flashing; `L 0`
      everything off.
- [ ] `s` shows the lamp masks and dimmer values.

## 2. Loose ends on the panel (none block the UI)

- [ ] Is B (corners) as steep at the bottom as C? `D 0 0x900 0`, `D 0 0x980 0`.
- [ ] What channel A drives, if anything — e.g. the daughter board's
      brightness: `L 1`, then `D 0 0 0` vs `D 0x158E 0 0`.
- [ ] Does lighting work with init **off** (`i`, `r`, then `l`)? If yes, the
      UI can skip the init frames.
- [ ] How long a PP3 lasts with everything lit; pick a proper 9 V supply for
      the build.

## 3. Hook the panel up to the UI

- [ ] `ui-prototype/PLAN.md`: the serial panel source — parse `MSG 0C …` /
      `MSG 0D …` lines into `PanelEvent`s, send `L`/`D`/`+`/`-` for the
      lighting. Keep the lamp state on the UI side and always send the whole
      mask: a corner sent without `0x40` turns the backlight off.

## Optional

- [ ] State B: try ACKing `18 03 80 9B` with `0x15`, and a frame sent after
      the 258 ms transition (`PROTOCOL.md` §12 q4).

## Housekeeping

- [ ] `captures/` is untracked. The `.log` files are git-ignored. Decide about
      the `.srzip` captures, e.g. move them to `pulseview/dumps/` as `.sr`,
      where the older captures are tracked.
- [ ] Delete `captures/2026-10-10-listener` (no extension): the same run at
      20 kHz, too slow to trust.
- [ ] `pulseview/setup.pvs` has uncommitted changes. Check the channel names
      before committing.
