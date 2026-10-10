# Audi RNS-e / Navigation Plus Reverse Engineering

**AI Note: The code and documentation in this repo was written by an AI and reviewed by a human. Regardless, double-check any information here, as I may have missed something.**

Reverse engineering the front-panel control board of an **Audi RNS-E** head
unit — the bit with the buttons, the scroll wheel and the volume knob — so it
can be driven from something other than an Audi.

**NOTE: All reverse engineering so far has been done on an `8P0 035 192 H` (for an Audi A3 8P). I don't expect this to change for other `192` versions, but I cannot confirm the protocol is the same for the `193` version.**

The panel is built around a Fujitsu MB90561A and talks to the main unit over a
9-pin connector using a small checksummed serial protocol. That protocol is now
understood well enough to boot the panel from an Arduino and read every button
and both encoders.

Everything here was derived from logic-analyzer captures of a bench setup, DMM
tracing, and the connector legend printed on the head unit's own case — no
vendor documentation was used beyond the publicly available MB90561A datasheet.

**Full findings: [`docs/PROTOCOL.md`](docs/PROTOCOL.md).** This README is the
map; that file is the territory.

Four documents, in decreasing order of how settled they are:

| document | what it covers | status |
|---|---|---|
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | the 9-pin serial link — framing, boot, keys, encoders | measured, mostly established |
| [`docs/BACKLIGHT.md`](docs/BACKLIGHT.md) | the LED driver chain and the analog stage | measured, one node left |
| [`docs/CANBUS.md`](docs/CANBUS.md) | using a head unit and the vehicle CAN bus to find the backlight command | connector established, experiment **not yet run** |
| [`docs/HARDWARE.md`](docs/HARDWARE.md) | what to buy for the above, and how to source a head unit to sniff | shopping list |

---

## Repository layout

```
docs/
  PROTOCOL.md      the protocol write-up — the main artefact of this project
  BACKLIGHT.md     the backlight driver chain and the analog stage. Supersedes
                   PROTOCOL.md §9
  CANBUS.md        plan for driving a head unit over CAN to capture the
                   head-unit-to-panel direction. Not yet executed
  HARDWARE.md      bench shopping list, and notes on sourcing a second head
                   unit to sniff and resell
  keymap.json      button/encoder map, machine-readable (generated)
  keymap.md        the same map as a table (generated)
  rns-e.drawio.svg circuit diagram (of what I was able to find so far)
  rns-e-pinout.png photo of the connector legend printed on the head unit,
                   transcribed in CANBUS.md §2
  datasheets/      where to put a local MB90561A datasheet (not redistributed)

src/rnse/
  rnse.py          offline decoder: sigrok .sr capture -> frames, messages,
                   key/rotary activity. stdlib only, no dependencies
  map_buttons.py   guided live mapping: prompts you to press each control and
                   writes keymap.json / keymap.md

arduino/
  listener/        boot the panel, decode its messages, stream them to USB.
                   This is the sketch you want for normal use
  fuzzer/          sweep byte values at the panel and watch what it answers
  handshake/       dumb two-stage probe: reset, wait, send bytes, observe.
                   Never reads, never decides — for isolating boot behaviour

pulseview/
  setup.pvs        PulseView session (channel names and decoders)
  dumps/           the captures the write-up is based on
```

Logic-analyzer channel convention throughout: `D0=Fuzzer`, `D1=Board`,
`D2=Marker`, `D3=Reset`.

## Hardware setup

> **Bench work only.** Everything below was done on a panel on a desk, powered
> from a bench supply. See [Safety and liability](#safety-and-liability) before
> putting any of it near a car.

### The connector

**Molex PicoBlade, 1.25 mm pitch, 9 pins.** Voltages measured against pin 2
with the panel connected to a real head unit:

| pin | signal                        | V vs GND |
| --- | ----------------------------- | -------- |
| 1   | VCC                           | +5.0     |
| 2   | GND                           | —        |
| 3   | RX (into the panel)           | +5.0     |
| 4   | TX (from the panel)           | +5.0     |
| 5   | PPG1 output — purpose unknown | +5.0     |
| 6   | reset — active low, runs HIGH | +5.0     |
| 7   | power / mute button           | +5.0     |
| 8   | rail monitor — VRAIL / 2      | +4.5     |
| 9   | +9 V LED rail, from head unit | +9.0     |

Two things on that list are _not_ on the serial bus and cannot be reached by
talking to the panel:

- **The power/mute button** (the volume-knob push) is not connected to the
  microcontroller at all. It shunts **pin 7 to ground** and the head unit senses
  it directly, so it produces no serial traffic. Read it as a plain active-low
  switch.
- **The backlight** is switched by a two-transistor high-side driver, TR5006
  gated by TR5015, fed from the +9 V rail the head unit supplies on pin 9. The
  8-pin IC — a Toshiba TA75W01FU dual op-amp, marked `5W01` with a `9.9` lot
  code — is *not* in the switching path; op-amp A is parked and op-amp B is a
  unity-gain buffer sending VRAIL / 2 back up pin 8 as a rail monitor. What
  drives TR5015's base is the one node still untraced. Full write-up in
  [`docs/BACKLIGHT.md`](docs/BACKLIGHT.md), which supersedes this paragraph if
  the two ever disagree.

### Wiring to an Arduino

Arduino Uno, using a bit-banged UART on D2/D3 so the hardware serial port stays
free for the PC — otherwise every debug line printed would also be delivered to
the panel as input.

```
D2  <- panel TX        (pin 4)
D3  -> panel RX        (pin 3)
D8  -> panel reset     (pin 6, active LOW: runs high, stops low)
GND <-> panel GND      (pin 2) REQUIRED
```

Reset should be pulled up with **15–30 kΩ** in normal use, but **omit that
resistor when driving the panel from an Arduino** — with it in place the reset
does not assert cleanly and the board never properly comes up.

## Quick start

Watch the panel live (replace `dev/ttyACM0` with the actual location of your board):

```sh
# flash arduino/listener/listener.ino, then
screen /dev/ttyACM0 115200
```

Re-map the buttons (or map a different panel variant):

```sh
uv run src/rnse/map_buttons.py --port /dev/ttyACM0 --out docs/keymap.json
```

Decode a capture offline:

```sh
uv run src/rnse/rnse.py pulseview/dumps/handshake.sr
uv run src/rnse/rnse.py pulseview/dumps/somethings-up.sr --from 15 --to 40
```

Capture at **≥ 500 kHz (ideally 1MHz)**. At 9600 baud a 20 kHz capture is only 2.08
samples/bit and silently corrupts data bits 5–7 while still looking plausible.

---

## What we know

### Transport — established

9600 baud, **8E1** (8 data bits, even parity, 1 stop), idle high, separate TX
and RX lines. 2296 consecutive frames decoded with zero parity and zero framing
errors. An early theory that this was 9-bit UART with an address bit was wrong;
the 9th bit is parity. This matters practically: no special hardware is needed,
`SERIAL_8E1` on any UART is enough.

### Frame format — established

```
[ADDR] [LEN] [payload × (LEN-2)] [CKSUM]

total length = LEN + 1
CKSUM        = sum(all preceding bytes) & 0xFF     (additive, not XOR)
```

Verified at LEN = 2, 3, 6 and 8 across hundreds of messages, 100% checksum
validity on every clean capture.

| ADDR   | LEN | meaning                             |
| ------ | --- | ----------------------------------- |
| `0x0C` | 8   | key state — 6-byte bitmap, absolute |
| `0x0D` | 6   | rotary delta — 4 channels, relative |
| `0x0F` | 2   | boot announcement                   |
| `0x18` | 3   | status / response — 1 payload byte  |

### Booting the panel — established

Reset is active low. Once released, the panel broadcasts `0F 02 11` every
52.6 ms and **ignores all input** until it receives the single bare byte
**`0x15`** — no framing, no reply, it just goes quiet and enters normal
operation. Neighbouring values behave differently (`0x14` is ignored, `0x16`
leads into a second waiting state), so this is a command from a small command
space, not a magic constant.

### Input — established

All 18 buttons and both encoders are mapped; see
[`docs/keymap.md`](docs/keymap.md). Key state is an **absolute** bitmap — press
sets a bit, release clears it, both are transmitted. Rotaries are **relative**
deltas, bit 7 = direction (0 = clockwise), bits 0–6 = detents accumulated since
the last report; d0 is the volume knob, d2 the scroll wheel.

The panel is **edge-driven, not polled**: after boot it is completely silent
until something changes. Multi-second gaps on the wire are normal, not a fault.
Every state change is sent exactly 4 times at ~59 ms, then silence.

---

## What we still need to discover

Ordered roughly by how much they unblock. The full list, with the evidence
behind each, is §11 of [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

1. ~~**The acknowledgement format (and if it needs any).**~~ **Solved
   (2026-10-10):** the bare byte `0x15`, as the head unit's firmware says
   (`docs/FIRMWARE.md` §5.5). With `listener.ino` sending it, each key and
   rotary report goes out once instead of 4×. The panel also ACKs the head
   unit's five init frames (`docs/PROTOCOL.md` §7).
2. **What resolves "state B."** Sending `0x16` at boot puts the panel into a
   second waiting state that broadcasts `18 03 80 9B` every 53.6 ms while
   ignoring input — structurally identical to the boot announcement, so it is
   very likely waiting for a reply of its own. `handshake.ino` takes a `STEPS[]`
   list to hunt for it.
3. **The command space around `0x14`/`0x15`/`0x16`.** Three adjacent values,
   three distinct behaviours. How large is it and what else is in there?
4. **The `0x18` status codes.** Four payloads seen — `0x01`, `0x06`, `0x40`,
   `0x80` — read tentatively as ACK / unknown / NAK / state-B. Inferred from a
   loose-byte sweep, not from well-formed frames; should be re-tested by
   sending complete messages.
5. **`0x22`.** The byte sweep suggests the panel recognises it as an address,
   but no traffic on it has ever been seen.
6. **Why the panel answers only every 2nd–3rd byte** during a sweep, regardless
   of the gap between bytes. The skip scales with the byte rate rather than
   being a fixed timeout, which weakens the "ACK timeout then re-arm" theory.
7. **What drives TR5015's base.** The last unknown node in the backlight
   circuit. The 8-pin IC is now identified — a Toshiba TA75W01FU dual op-amp,
   and a bystander to the switching path — and everything downstream of that
   base is traced. All nine connector pins are accounted for and none is a
   backlight enable, so the drive must come from the MCU, which implies a
   serial command nobody has seen. See
   [`docs/BACKLIGHT.md`](docs/BACKLIGHT.md).
8. **What PPG1 on connector pin 5 carries.** It is a hardware PWM output from
   the MB90561A that has never been captured. Worth an LA channel next time the
   panel is on the bench. Four other PPG channels are also unaccounted for, and
   one of them is the prime suspect for the backlight drive.
9. **Everything the head unit says to the panel.** Every message decoded so far
   travels panel → head unit, because every capture so far was taken with the
   panel driven by an Arduino that only knows the commands already guessed. A
   powered head unit knows all of them. [`docs/CANBUS.md`](docs/CANBUS.md) is
   the plan for putting one on the wire. Two things point the same way: the
   connector legend shows **no illumination pin on any connector**, and a head
   unit powered on the bench with no CAN boots to its PIN screen while the
   attached, powered panel stays dark. So the stimulus has to arrive over CAN.

## Status

Bench-only, and the code reflects that: it is instrumentation for answering the
questions above, not a library. `rnse.py` and `map_buttons.py` are standalone
scripts.

---

## Safety and liability

This is experimental bench instrumentation, published so others can learn from
it. It is **not** a product and carries no warranty of any kind.

- The panel is driven here from a bench supply with its reset line under
  external control. Wiring third-party electronics into a vehicle is entirely at
  your own risk.
- A car is a shared electrical and data environment. Injecting signals into it —
  or loading a bus that other modules depend on — can disturb unrelated systems,
  trip fault codes, drain the battery, or leave a module in a state that needs a
  dealer tool to clear.
- Modifying a vehicle may void warranties, fall foul of local roadworthiness
  rules, and interfere with safety-relevant equipment. Check what applies where
  you are.
- Nothing here has been tested for use while a vehicle is in motion, and it
  should not be.

You are responsible for your own hardware, your own vehicle, and your own
safety.

## License

Two licenses, because this repository holds two different kinds of work. Both
require that you credit the author.

| what                                                  | license                                                                             | file                             |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------- |
| **Code** — `src/`, `arduino/`                          | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)                            | [`LICENSE`](LICENSE)             |
| **Docs and captures** — `docs/`, `pulseview/`, README | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)                            | [`LICENSE-docs`](LICENSE-docs)   |

Apache-2.0 on the code because it includes an explicit patent grant, so anyone
who wants to build something real on top of this — an adapter, a retrofit — does
not have to wonder. CC BY 4.0 on the write-up and the captures because those are
prose and data, not software, and CC BY is the license people actually recognize
as *credit the author*.

In practice, if you use any of this, keep the copyright notice and say where it
came from:

> Protocol details from the [rnse project](https://github.com/RedRoserade/rns-e)
> by André Carvalho, CC BY 4.0.

**The protocol itself is not covered by either license, and cannot be.** Frame
layouts, checksum algorithms and the fact that `0x15` boots the panel are
facts about how the hardware behaves — they are not anyone's copyright,
including mine. Reimplement them freely. The licenses cover *this* description
and *this* code.

Third-party material is excluded: no vendor datasheet is redistributed here (see
[`docs/datasheets/`](docs/datasheets/)).

## Trademarks

**Audi**, **RNS-E**, **Navigation Plus** and **Volkswagen** are trademarks of
AUDI AG / Volkswagen AG, who specified and sold the unit. **Aisin** is a
trademark of Aisin Corporation — the RNS-E was built by **Aisin AW Co., Ltd.**,
which merged into Aisin Corporation in 2021, so units of this vintage carry Aisin
AW markings. All are used here purely descriptively, to identify the hardware
this project interoperates with.

This project is an independent effort. It is **not affiliated with, authorised
by, endorsed by, or connected to** AUDI AG, Volkswagen AG, Aisin Corporation, or
any of their subsidiaries. **MB90561A** is a Fujitsu part designation, now held
by Infineon Technologies AG via Cypress Semiconductor; that datasheet is not
redistributed here (see [`docs/datasheets/`](docs/datasheets/)).
