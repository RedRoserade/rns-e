# Next steps

Where the bench work stopped on 2026-10-10, and what to do next. Findings are
in the docs; this file is the to-do list. Delete items as they are done.

## Where things stand

- **Head unit (CAN):** revived, boots to the PIN screen. `0x635` byte 0 sets
  the display backlight; byte 1 lit no button LEDs on two panels. The NM ring
  holds with `can_backlight.py` (`CANBUS.md` §3, §4.2).
- **Panel link (Arduino, no head unit):** the panel accepts `0x15` as the ACK,
  which stops its 4× retry, and ACKs all five head-unit init frames
  (`PROTOCOL.md` §6, §7), every one on the first try with
  `arduino/listener`. `0x16` + frame puts it in state B instead.
- **Not yet tried:** anything with the LED rail fed. Every backlight test so
  far ran with pin 9 unpowered, so "no LEDs" has meant nothing.

## 1. Feed the LED rail and test the backlight — the main task

Wiring: https://claude.ai/artifact/FvscwtBstZmHNBJuvVsW1E
(PP3 + → panel pin 9, PP3 − → panel pin 2. **Never 9 V on pin 1.**)

Before:

- [ ] PulseView: check the channel names (D0 = Arduino TX "Fuzzer",
      D1 = panel TX "Board", D3 = Reset). They have flipped before.
      Sample at 1 MHz. Optionally D4 on pin 5 (PPG1, never captured).
- [ ] Multimeter ready on pin 9 and pin 8.

Sequence:

1. [ ] USB in, `r`, wait for `# init done`. Battery still off.
2. [ ] Connect the battery. Pin 8 should read ≈ 4.5 V (rail ÷ 2). Note
       whether any LED lights **before** sending anything: the last init frame
       is already a dimmer frame (`06 0E 00 00 00 00 30 70 …`, C = full
       period, A = B = 0).
3. [ ] `b` — sends the dimmer frame at half of each period. Note the LEDs.
4. [ ] One channel at a time, with `D A B C` (periods: A `0x158E`,
       B `0x09B0`, C `0x3070`):
       - `D 0 0 0`
       - `D 0x158E 0 0`, then `D 0 0x9B0 0`, then `D 0 0 0x3070`
       - for whichever channel lights: half, quarter, zero — is it graded?
5. [ ] `+` / `-` to step all three by a tenth of their period.
6. [ ] Measure pin 9 under load, and how long the PP3 holds up.
7. [ ] Repeat a lit setting with init **off** (`i`, `r`, then `D …`). Does the
       dimmer frame still work without the init sequence?

Record for each step: the frame sent, the panel's reply (ACK / NAK / none),
which LEDs changed. The question being answered: which of A, B, C drives the
button backlight (`FIRMWARE.md` §5.2.1 says C comes from `0x635` byte 1), and
whether it is graded or on/off.

If nothing lights at all: probe TR5015's base during a `D` sweep
(`BACKLIGHT.md` §8, `CANBUS.md` T8). A level that follows the sweep means the
frame works and the problem is downstream.

## 2. Softkey lamps (`ADDR 0x07`)

The listener cannot send this frame yet. Add a raw-frame command (e.g.
`F 07 06 00 00 00 04`, with the checksum computed) and run the list in
`FIRMWARE.md` §6 item 6:

- [ ] `o3` = `04`, `08`, `10`, `20` one at a time: which corner lights?
- [ ] `o3` = `00`: all off.
- [ ] The other bits (`o3` `01`, `02`, `40`, `80`; `o2` `01`) and one odd bit
      (`o1` `04`).

## 3. Back to the head unit

Once the panel side is understood:

- [ ] Head unit + panel + analyser on the panel link. Sweep `0x635` byte 1
      with `can_backlight.py` and look for `06 0E …` frames. Do C and C' follow
      byte 1? (`CANBUS.md` §3)
- [ ] Capture the real head unit's boot on the panel link, and compare its
      init and ACK timing with what the listener does.

## Optional

- [ ] State B: try ACKing `18 03 80 9B` with `0x15`, and a frame sent after
      the 258 ms transition (`PROTOCOL.md` §11 q4).

## Housekeeping

- [ ] `captures/` is untracked. The `.log` files are git-ignored. Decide about
      the `.srzip` captures, e.g. move them to `pulseview/dumps/` as `.sr`,
      where the older captures are tracked.
- [ ] Delete `captures/2026-10-10-listener` (no extension): the same run at
      20 kHz, too slow to trust.
- [ ] `pulseview/setup.pvs` has uncommitted changes. Check the channel names
      before committing.
