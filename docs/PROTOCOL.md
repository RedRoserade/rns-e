# RNS-E front panel — protocol notes

Reverse engineering of an Audi RNS-E control board built around a Fujitsu
MB90561A. The panel connects to the main unit over a 9-pin connector and
speaks a simple checksummed serial protocol.

Status: transport, frame format, the boot handshake, and the full input map
(18 buttons + 2 rotaries) are **established**. Since 2026-10-10 so is the
link layer from the head unit's side: the panel accepts the `0x15` ACK, which
stops its retries (§6), and ACKs all five init frames from the head unit's
firmware (§7). Since 2026-10-12 the **lighting is established** too: the lamp
frame `0x07` switches the button backlight and every indicator, and the dimmer
frame `0x06` sets their brightness (§8). Together that is everything needed to
drive the panel without a head unit. Each claim below is marked with its
confidence.

---

## 1. Physical / transport

| property | value | confidence |
|---|---|---|
| baud | 9600 | **measured** — min pulse width 104 µs at 1 MHz sampling, with clean 2/3/4/7-bit multiples (209/314/419/733) |
| format | **8E1** — 8 data bits, EVEN parity, 1 stop | **established** — 2296 board frames decoded with 0 parity errors and 0 framing errors |
| idle | high | measured |
| direction | panel TX and panel RX are separate lines | measured |

### It is NOT 9-bit UART

An early working theory was 9-bit UART with an address bit (plausible for a
multidrop automotive bus). It is wrong. The 9th bit is a **parity bit**:

- All 7 distinct bytes in the first capture satisfied even parity, 7/7.
- On a clean 1 MHz capture, 2296 consecutive board frames decoded as 8E1 with
  zero parity errors. If the 9th bit were an address flag, it would be set only
  on the first byte of each message and parity would fail constantly.

### Sampling rate matters

Do not capture below ~500 kHz. At 20 kHz a 9600 baud signal is only 2.08
samples/bit, which corrupts data bits 5–7 about 15% of the time while still
looking plausible. 1 MHz is comfortable.

---

## 2. Frame format

```
[ADDR] [LEN] [payload × (LEN-2)] [CKSUM]

total length = LEN + 1
CKSUM        = sum(all preceding bytes) & 0xFF
```

**Established.** Verified at LEN = 2, 3, 6 and 8, across hundreds of messages,
with 100% checksum validity on every clean capture.

Examples:

```
0F 02 11                     LEN=2, no payload      0x0F+0x02             = 0x11
18 03 40 5B                  LEN=3, payload 40      0x18+0x03+0x40        = 0x5B
0D 06 01 00 00 00 14         LEN=6, payload 01...   0x0D+0x06+0x01        = 0x14
0C 08 00 00 08 00 00 00 1C   LEN=8, payload 00...   0x0C+0x08+0x08        = 0x1C
```

Note it is an **additive** checksum, not XOR. For small payloads the two
coincide (no carries), which is initially misleading; LEN=8 messages with
larger values disambiguate it.

---

## 3. Known addresses

| ADDR | LEN | meaning | confidence |
|---|---|---|---|
| `0x0C` | 8 | key state — 6-byte bitmap, absolute | **established** |
| `0x0D` | 6 | rotary delta — 4 bytes, relative | **established** |
| `0x0F` | 2 | boot announcement, broadcast until `0x15` is sent | **established** |
| `0x18` | 3 | status / response — 1 payload byte | inferred |

**Firmware cross-check (`FIRMWARE.md` §5.5).** The head unit's receive code
confirms all four rows and names more. Every address below comes from
disassembly. On the bench (2026-10-10), the panel accepted `0x15` as the ACK
and ACKed the init frames `0x02`, `0x03`, `0x0A`, `0x09` and `0x06` (§7);
the rest have not been sent.

| direction | ADDR | LEN | from firmware |
|---|---|---|---|
| panel → HU | `0x04` | any | accepted, ignored |
| panel → HU | `0x08`, `0x0B`, `0x10`, `0x11`, `0x12` | 6, 3, 3, 3, any | accepted, ACKed, no action |
| panel → HU | `0x18` | 3 | NAK of the head unit's last frame → retransmit |
| HU → panel | `0x00` | 3 | `00 03 2E 31`, resync after 3 timeouts |
| HU → panel | `0x01`, `0x02`, `0x03`, `0x09`, `0x0A` | 6, 12, 15, 6, 7 | config frames; `02`, `03`, `0A`, `09` are the init sequence |
| HU → panel | `0x06` | 14 | **dimmer**: brightness of the lamps (§8, `FIRMWARE.md` §5.2.1) |
| HU → panel | `0x07` | 6 | **lamps**: button backlight and indicators on/off/flash (§8, `FIRMWARE.md` §5.6) |
| HU → panel | `0x0E` | ? | reserved; nothing in the firmware builds it |
| HU → panel | `0x15` | bare byte | **ACK** |
| HU → panel | `0x16` | bare byte | **ACK, with the next frame following straight after** |

---

## 4. `ADDR 0x0C` — key state

```
0C 08 P0 P1 P2 P3 P4 P5 CK
```

Six payload bytes = a bitmap of up to 48 keys. **Absolute state**, not events:
a press sets a bit, a release clears it, and both transitions are transmitted.
An all-zero payload (`0C 08 00 00 00 00 00 00 14`) means nothing is held.

### Bit → button map — **established**

All 18 front-panel buttons have been identified by pressing each one under
`map_buttons.py`, 3 presses each, with no bit claimed by two controls. The
machine-readable version is `keymap.json`; `keymap.md` is generated from it.

| control | bit | payload byte | mask |
|---|---|---|---|
| info | P0.1 | 0 | `0x02` |
| nav | P0.2 | 0 | `0x04` |
| tel | P0.3 | 0 | `0x08` |
| name | P0.5 | 0 | `0x20` |
| cd_tv_sd_media | P0.6 | 0 | `0x40` |
| radio | P0.7 | 0 | `0x80` |
| top_left_quad | P1.1 | 1 | `0x02` |
| top_right_quad | P1.2 | 1 | `0x04` |
| return | P1.3 | 1 | `0x08` |
| flip_screen | P1.5 | 1 | `0x20` |
| setup | P1.6 | 1 | `0x40` |
| car | P1.7 | 1 | `0x80` |
| fwd | P2.3 | 2 | `0x08` |
| back | P2.5 | 2 | `0x20` |
| bottom_right_quad | P2.6 | 2 | `0x40` |
| bottom_left_quad | P2.7 | 2 | `0x80` |
| eject | P3.7 | 3 | `0x80` |
| scroll_click | P5.4 | 5 | `0x10` |

The four quad buttons are the softkeys around the scroll wheel; `fwd` / `back`
are the seek keys; `flip_screen` is the display tilt key. `cd_tv_sd_media` is labelled `CD/TV` on European `192` units, while `CD/SD` in American `192` units, and `Media` on `193` units.

### Unused bits — structure, INFERRED

18 of the 48 bits are accounted for. The unused ones are not scattered at
random:

| byte | used | unused |
|---|---|---|
| 0 | 1, 2, 3, 5, 6, 7 | **0, 4** |
| 1 | 1, 2, 3, 5, 6, 7 | **0, 4** |
| 2 | 3, 5, 6, 7 | 0, 1, 2, 4 |
| 3 | 7 | 0–6 |
| 4 | — | all |
| 5 | 4 | all but 4 |

In bytes 0–2 bits **0 and 4 are never set**, and bytes 0 and 1 are otherwise
completely full. That looks like a scan matrix in which the low bit of each
nibble is not a key position, rather than 12 buttons that happen to be absent —
but it is a pattern in one panel's data, not a proven encoding. Bytes 3–5 are
nearly empty, so the bitmap is sized well above what this panel populates and
is probably shared across RNS-E variants with more keys.

**The volume knob's push (power/mute) is not in the map, and never will be.**
It is not wired to the microcontroller at all — it shunts connector pin 7 to
ground and the head unit senses it directly (§10). Pressing it produces no
serial traffic. So the spare bits above are not hiding it.

---

## 5. `ADDR 0x0D` — rotary encoders

```
0D 06 d0 d1 d2 d3 CK
```

Four payload bytes, one per encoder channel. Each is a **relative delta**:

```
bit 7    direction (0 = one way, 1 = the other)
bits 0-6 number of detents since the last report
```

**Relative, not absolute** — there is no return-to-zero message after a turn,
unlike the key bitmap. Detents accumulate between reports, so a fast spin
coalesces into one message (`0x03` = three detents in one report) rather than
flooding the bus.

### Channel assignment — **established**

| control | channel | CW / up | CCW / down |
|---|---|---|---|
| volume_knob | d0 | bit 7 = 0 | bit 7 = 1 |
| scroll_wheel | d2 | bit 7 = 0 | bit 7 = 1 |

Confirmed by turning each knob under `map_buttons.py`: each direction landed on
a single channel with a single consistent direction bit, and the two knobs
landed on different channels. The direction encoding is the same on both
channels, so bit 7 is a sign bit for the whole message, not a per-channel
quirk.

**d1 and d3 have never been non-zero** in any capture, before or after mapping.

---

## 6. Timing and repeat behaviour

The panel is **edge-driven, not polled**. Once past the boot announcement (§7)
it transmits only when something changes and is completely silent otherwise —
gaps of over 3 s with nothing on the wire are normal and not a fault.

Every state change is sent **exactly 4 times**, then silence:

| message | repeat interval |
|---|---|
| `0x0C` keys | ~58.8 ms |
| `0x0D` rotary | ~56.7 ms |

Response latency to a received byte is 1.16–1.23 ms. A byte occupies 1.146 ms
at 9600 8E1, so the panel replies within ~50 µs of the stop bit.

### The 4× repeat is a retry — **established** (2026-10-10)

With the listener answering every valid report with the bare byte `0x15`,
every key and rotary report was sent **once**
(`captures/2026-10-10-listener-proper.srzip`, `…-listener-init.srzip`). The
`0x15` went out 2–3 ms after the report ended. So the panel repeats until
ACKed, gives up after 4 tries, and the ACK is `0x15`, as the firmware says.
The reasoning that led here, kept for the record:

Repeating an *absolute* bitmap 4× is harmless. Repeating a *relative* rotary
delta 4× would quadruple the movement if the receiver summed them. The most
likely explanation is that **the panel repeats until acknowledged and gives up
after 4 attempts**, and we always observe 4 because nothing has ever answered
it. During the fuzz sweep only 2–3 repeats appeared, consistent with this.

This is the single most important open question. It is directly testable: send
an ACK and see whether the repeat count drops below 4.

**Firmware cross-check:** the head unit answers every valid panel frame with
the bare byte **`0x15`** (`FIRMWARE.md` §5.5). It is the same byte that ends
the boot announcement: that is the head unit ACKing `0F 02 11`. So the ACK to
send after each `0x0C`/`0x0D` report is `0x15`. Whether the panel then stops
repeating still needs a capture.

---

## 7. Reset line and the boot announcement

Connector pin 6. Active **low**: the board runs when the pin is high and stops
when held low. It should be pulled up with 15–30 kΩ in normal use (see datasheet), but that
resistor **should be omitted when driving the panel from an Arduino** — with it
in place the reset may not assert cleanly. Bypassing it changed the panel's
behaviour completely, so the reset circuit matters more than a single GPIO
usually would. See §9.

### `ADDR 0x0F` — boot announcement

After reset is released the panel broadcasts `0F 02 11` (LEN=2, no payload)
every **52.6 ms**, continuously, and **sends no other activity while doing so**.

> **Correction.** This was previously written up as a fault caused by a
> floating reset line. That was wrong. It is normal boot behaviour. The
> *silence* observed in `dump-v2.sr` was the anomaly — that capture had the
> reset pull-up fighting the Arduino, so the board likely never cleanly booted.

Observed in `somethings-up.sr` (reset pull-up bypassed):

| | |
|---|---|
| announcement period | 52.6 ms, uninterrupted |
| resumed after reset release | +40 ms |
| bytes received during the phase | 21 (`0x00`–`0x14`), **all ignored, zero replies** |
| phase ended | on receiving `0x15` (see below) |
| announcements after that | none, for the remaining 75 s |

That capture corroborates the command table below exactly: every byte from
`0x00` to `0x14` was ignored, `0x15` ended the phase, and the `0x16` that
followed 400 ms later drove it into state B — the first `18 03 80 9B` appears
258 ms after that `0x16`, matching `handshake-0x16.sr` to the millisecond.

It did **not stay** in state B, though: the sweep kept sending bytes, and the
`18 03 80 9B` messages there come in bursts of 3 with gaps rather than the
uninterrupted 53.6 ms stream seen when nothing else is transmitted. Key and
rotary reports resumed later in that capture. So something in the continuing
byte stream knocks the panel back out of state B — which value is unknown, and
is a second way in besides finding state B's proper reply.

### The announce phase is ended by sending `0x15` — **SOLVED**

Sending the single byte **`0x15`** stops the broadcast immediately and puts the
panel into normal operation. Confirmed in `handshake.sr`:

| event | time |
|---|---|
| reset released | 0.4971 s |
| first announcement | 0.5378 s (+40.7 ms) |
| 10 announcements @ 52.6 ms | 0.538 → 1.011 s |
| **`0x15` transmitted** | 1.0215 s |
| next announcement due | 1.0634 s — **never came** |
| announcements afterwards | **0** |

This also rules out the timeout/ripeness theory: the panel had been announcing
for only **0.48 s / 10 announcements**, not the 24.8 s / ~470 of the capture
where it was first noticed. `0x15` works immediately.

Properties of the handshake:

- **A single bare byte is sufficient.** No `[ADDR][LEN][CKSUM]` framing needed.
- **The panel does not reply to it.** No `18 03 xx`, nothing — it is accepted
  silently and the panel simply goes quiet. This fits the ACK/NAK reading in
  §9: `18 03 xx` is only emitted for bytes the panel does *not* accept.
- Afterwards the panel is fully silent until a key or rotary changes; gaps of
  3.1 s with nothing on the wire were observed.

### `0x14` / `0x15` / `0x16` are three different commands

Adjacent values produce three distinct behaviours, so these are **commands
from a small command space, not a magic constant**:

| byte | effect |
|---|---|
| `0x14` | ignored — the announcement simply continues |
| `0x15` | announcement stops → **normal edge-driven operation** |
| `0x16` | announcement stops → after 258 ms, **state B** (below) |

### State B — the `18 03 80 9B` broadcast

`0x16` does not fail. It stops the boot announcement and moves the panel into a
second waiting state, confirmed in `handshake-0x16.sr`:

| | |
|---|---|
| `0x16` sent | 0.5245 s |
| last `0F 02 11` | 0.5138 s — 10.7 ms before the byte, same as `0x15` |
| first `18 03 80 9B` | 0.7828 s — **258.3 ms after** |
| thereafter | 45 messages, gap min = median = max = **53.6 ms**, to end of capture |
| key presses | **none reported** — input ignored, exactly as in state A |

The two states are structurally identical — a fixed message repeating forever
at ~53 ms while input is ignored:

| state | broadcast | period | resolved by |
|---|---|---|---|
| A (boot) | `0F 02 11` | 52.6 ms | `0x15` |
| B | `18 03 80 9B` | 53.6 ms | **unknown** |

**Firmware reading (`FIRMWARE.md` §5.5):** `0x16` means "ACK, and a frame
follows". The head unit only sends it with a queued command right behind it.
On its own, the panel waits for a frame that never comes. `18 03 80 9B` is
byte-for-byte the head unit's own NAK for "no handler for this address", so
the panel is most likely reporting the missing or unusable frame, and repeating
because nobody ACKs it. This is an inference: the panel's own code has not been
read.

So state B is very likely **waiting for a reply of its own**. Finding it needs
a two-stage probe: `0x16`, then a candidate sent after the 258 ms transition
completes. `handshake/handshake.ino` takes a `STEPS[]` list for exactly this.

**Bench result (2026-10-10): a frame straight after `0x16` does not avoid
state B.** The listener answered `0F 02 11` with `16` followed at once by the
first init frame `02 0C … 7D` (`captures/2026-10-10-listener.srzip`). The panel
did not ACK it. About 273 ms after that frame, and after each of two
retransmits, it sent `18 03 80 9B`. After the last retransmit it settled into
the 53.6 ms broadcast. The same frame after a bare `0x15` was ACKed at once
(below). So in this state the panel does not take `0x16` as "ACK + frame
follows", whatever the head unit's own code does with it.

### This resolves the "258 ms latency" anomaly

Earlier notes recorded an unexplained 258 ms reply latency in
`somethings-up.sr`, contrasted against 1.2 ms elsewhere. It was never a reply
latency: **258 ms is the state-transition delay into state B**, and the
`18 03 80 9B` messages are a continuous broadcast, not bursts of retries.

### Boot sequence, end to end

```
reset LOW  ->  reset HIGH
               +40 ms   panel begins broadcasting  0F 02 11  every 52.6 ms
               send 0x15
               panel stops broadcasting, enters normal edge-driven operation
               (silent until a key or rotary changes)
```

### The head unit's init sequence — **accepted by the panel** (2026-10-10)

After the `0x15`, the listener sent the five init frames from the head unit's
firmware (`FIRMWARE.md` §5.5), each after the previous one was ACKed. The
panel answered every one with `0x15` within ~1 ms of its last byte
(`captures/2026-10-10-listener-init.srzip`):

```
0.559  panel  0F 02 11
0.565  HU     15
0.586  HU     02 0C 40 1D 4B 42 40 00 40 01 FF 05 7D         panel 15
       HU     03 0F 3C 0A 02 0A 04 0A 04 0A 04 0A 04 0A 0A A6 panel 15
       HU     0A 07 00 FF 1C FF 1C 47                         panel 15
       HU     09 06 00 00 0F 06 24                            panel 15
       HU     06 0E 00 00 00 00 30 70 00 00 00 00 00 00 B4    panel 15
```

A 20 ms pause between the `0x15` and the first frame was used; whether it is
needed is untested. Afterwards keys and rotaries reported normally, once each.
These are the **first head-unit → panel frames confirmed on the wire.** What
`02`, `03`, `0A` and `09` configure is still unknown. The last one is a dimmer
frame that leaves everything dark (B = B' = 0, C at full off-time; §8), so
nothing lights until a real dimmer frame and a lamp frame follow.

(In that capture, the listener retransmitted frames 2–5 once each although the
panel had ACKed them. That was the Arduino misreading the ACK while its USB
serial interrupt was busy, not the panel. With bytes read with interrupts off,
every frame is ACKed on the first try and the whole init takes 120 ms, from
`0F 02 11` to the last ACK: `captures/2026-10-10-listener3.srzip`.)

---

## 8. Lighting — `0x07` lamps and `0x06` dimmer — **established** (2026-10-12)

Every LED on the panel is fed from **connector pin 9** (+9 V; a PP3 works on
the bench). Nothing lights without it, whatever is sent. Two head-unit frames
control them: `0x07` decides **which** lamps are on, `0x06` decides **how
bright**. A lamp needs both: an ON bit, and a non-zero on-time on its dimmer
channel. Both frames are ACKed with `0x15` like any other. Mapped with
`arduino/listener`; the frame layouts come from the head unit's firmware
(`FIRMWARE.md` §5.2.1, §5.6).

### `ADDR 0x07` — lamps

```
07 06  F1 F0  N1 N0  CK

N1:N0  ON mask,    u16 big-endian
F1:F0  FLASH mask, u16 big-endian, same bit layout
```

| bit | lamp | dimmer channel |
|---|---|---|
| `0x0001` | SD card + eject daughter board | — |
| `0x0002` | eject button | — |
| `0x0004` | NE softkey indicator | B |
| `0x0008` | NW softkey indicator | B |
| `0x0010` | SE softkey indicator | B |
| `0x0020` | SW softkey indicator | B |
| **`0x0040`** | **main button backlight** | **C** |
| `0x0080` | scroll wheel dial | C |
| `0x0100` | volume dial | C |
| `0x0200`–`0x8000` | nothing visible | — |

- **The frame is the whole lamp state, and the backlight is one of its bits.**
  Each frame replaces the last. Sending a corner on its own (`… 00 04`) turns
  the backlight **off**; to light a corner and keep the backlight, send both
  bits (`… 00 44`). Whoever drives the panel has to keep the lamp state and
  OR the bits together.
- Any combination works (`N0` = `0x3C` lights all four corners). The head unit
  only ever sets one corner at a time; the panel does not care.
- A FLASH bit makes its lamp flash. Each lamp is a pair of bits in the head
  unit's 32-bit lamp word (2k = on, 2k+1 = flash), split by parity into the two
  masks. The head unit never sets a flash bit.

| frame | lights |
|---|---|
| `07 06 00 00 00 40 4D` | backlight only |
| `07 06 00 00 00 44 51` | backlight + NE |
| `07 06 00 00 00 04 11` | NE only — backlight **off** |
| `07 06 00 00 01 C0 CE` | backlight + both dials — what the head unit sends with the lights on |
| `07 06 00 00 00 00 0D` | everything off |

### `ADDR 0x06` — dimmer

```
06 0E  A  B'  C  A'  B  C'  CK      each u16 big-endian

A' = 0x158E − A     B' = 0x09B0 − B     C' = 0x3070 − C
```

Three PWM channels, each value sent with its complement against the
channel's period. **B and C are off-times**: the brightness follows B' and C'.
0 is full, the period is off.

| channel | period | drives |
|---|---|---|
| A | `0x158E` | nothing visible |
| B | `0x09B0` | the four softkey indicators |
| C | `0x3070` | the main button backlight and both dials |

Full brightness, A = B = C = 0: `06 0E 00 00 09 B0 00 00 15 8E 00 00 30 70 10`.

Graded, not on/off. Backlight sweep (lamp `0x0040`, A = B = 0):

| C | on-time C' | duty | backlight |
|---|---|---|---|
| `0` | `0x3070` | 100 % | brightest |
| `0x800`, `0x1838` | | 83 %, 50 % | no visible difference from full |
| `0x2800` | `0x870` | 17 % | visibly dimmer |
| `0x2EFF` | `0x171` | 3.0 % | dimmest visible, dim room |
| `≥ 0x3000` | `≤ 0x70` | < 1 % | off |

The two dials are on C as well. With lamps `0x01C0` lit, C at its period
turned the backlight and both dials off; B at its period and A at its period
left them on.

The eye is roughly logarithmic, so the visible range is the bottom few percent;
step brightness by doubling and halving the on-time, not linearly. The corner
indicators: B = 0 is brighter than half, B = `0x9B0` is off; not swept further.

On a head unit, B follows `0x635` byte 0 (display brightness) and C follows
byte 1 (KL58s, the instrument-lighting dimmer), and the backlight bit is set
when the dimmer state says the lights are on (`FIRMWARE.md` §5.2.1, §5.6). The
init sequence's dimmer frame (§7) has B = B' = 0 and C at full, so after boot
the panel is dark until both frames are sent.

### Not yet known

- What channel A drives, if anything. It does nothing to the main panel
  (lamps `0x01C0` lit: A = `0x158E` changes nothing). The SD card daughter
  board (`0x0001`) is the remaining candidate; it was not fitted on the bench.
- Whether `0x0001` / `0x0002` have a dimmer channel (A is the candidate).
- Whether the corner channel B shows the same steep bottom end as C.

---

## 9. Response to arbitrary received bytes (INFERRED)

Sweeping all 256 byte values at the panel produced replies on `ADDR 0x18`:

| trigger | reply | reading |
|---|---|---|
| `0x0C`, `0x0F`, `0x22` | `18 03 01 1C` | recognised address → ACK |
| everything else | `18 03 40 5B` | unrecognised → NAK / error |
| (seen once) | `18 03 06 21` | third status code, unexplained |
| post-announce state | `18 03 80 9B` | fourth code; the *only* reply in that state |

Four payload codes are now known: `0x40`, `0x01`, `0x06`, `0x80`. `0x18`
messages repeat **3× at ~53.6 ms**, a different cadence from the 4× / 58.8 ms
used by key reports.

### The 258 ms figure was not a latency — RESOLVED

An earlier note here recorded an unexplained 258 ms reply latency in
`somethings-up.sr` versus 1.2 ms elsewhere. `handshake-0x16.sr` shows what it
actually is: the **transition delay into state B** after receiving `0x16`
(§7). Genuine replies remain ~50 µs after the stop bit.

`0x0C` and `0x0F` are known valid ADDR values, which is what makes the
"recognised address" reading attractive; `0x22` is then a third address whose
traffic has not been observed. This is **inference from a loose-byte sweep**,
not from well-formed frames, and should be re-tested by sending complete
`[ADDR][LEN][…][CKSUM]` messages.

### The sweep never covers the whole value space

After replying, the panel skips bytes. With a 150 ms gap it answered exactly
every *second* byte (306 ms = 2× the byte period), so bytes 0x25–0xFF odd were
never really tested — "no response" was confounded with "arrived while deaf".

`fuzzer.ino` was raised to a 400 ms gap to fix this. **It did not work.** In
`somethings-up.sr` the panel still answers only every 2nd or 3rd byte, at
809 ms / 1214 ms — again exactly 2× and 3× the byte period. Whatever gates the
replies scales with the byte rate rather than being a fixed timeout, which
weakens the "ACK timeout then re-arm" theory in §6.

---

## 10. Connector and hardware

The panel connects through a **Molex PicoBlade, 1.25 mm pitch, 9 pins**.

### Pinout — **established**

Voltages are DC, measured against pin 2 with the panel connected to the actual
radio and running.

| pin | signal | V vs GND | notes |
|---|---|---|---|
| 1 | VCC | +5.0 | supply |
| 2 | GND | — | reference |
| 3 | RX | +5.0 | board-level RX — **into** the panel |
| 4 | TX | +5.0 | **from** the panel |
| 5 | PPG1 output | +5.0 | purpose unknown |
| 6 | reset | +5.0 | active low: panel runs HIGH, stops LOW |
| 7 | power button | +5.0 | shunted to pin 2 by the button on the volume dial — see below |
| 8 | rail monitor **out** | +4.5 | pin 9 ÷ 2, buffered by an op-amp, for the head unit to read (`BACKLIGHT.md` §7) |
| 9 | LED rail **in** | +9.0 | feeds every LED on the panel (§8). **Never connect to pin 1** |

Every signal pin idles at +5 V, which is consistent with all of them being
pulled up on the head-unit side.

### The power / mute button is not on the bus — **established**

The volume knob's push is **not connected to the microcontroller at all**. It
simply shunts **pin 7 to pin 2 (ground)**. The head unit senses it directly.

This is why it never appeared in the key bitmap (§4) and why it never will:
pressing it produces no serial traffic whatsoever. If you are replacing the
head unit, this button must be read as a plain grounding switch on pin 7 — the
+5 V idle above is the head unit's pull-up, so it reads as active-low.

> **Correction.** Earlier notes described this as "a shunt to a power button
> (appears unconnected)". It is connected; it just does not go anywhere near
> the MCU.

### Reset needs a pull-up — but not with an Arduino

Pin 6 should be pulled up with a **15–30 kΩ** resistor for normal operation.

**When driving the panel from an Arduino, omit the resistor.** With it in
place the reset does not assert properly — the pull-up fights the GPIO and the
board does not come up cleanly. This is not a theoretical concern: it is what
corrupted `dump-v2.sr` (see §7), where the panel apparently never booted at all
and the resulting silence was misread as a protocol state.

### Pins 8 and 9 — the LED rail — **established**

Pin 9 is the +9 V supply for every LED on the panel, switched on the panel
side; pin 8 is that rail halved and buffered by a TA75W01FU dual op-amp, going
back to the head unit. The op-amp is **not** in the switching path. The LEDs are
switched by the MCU, commanded over the serial link (§8). Details in
`BACKLIGHT.md`.

> **Correction.** Earlier revisions said this IC was a backlight driver and that
> "no amount of UART traffic will light the panel". Both were wrong: the IC is
> a rail monitor, and the lamp and dimmer frames light everything (§8). The
> earlier "+8.0 V" reading was a rounded 9.0 V.

### PPG1

Pin 5 is driven from the MB90561A's **programmable pulse generator** peripheral
— i.e. it is a hardware PWM output from the panel, not a plain GPIO. What the
head unit does with it is unknown. It has never been captured; a PWM output is
worth putting on the logic analyzer next time the panel is on the bench.

---

## 11. Tooling

| file | purpose |
|---|---|
| `src/rnse/rnse.py` | decode a sigrok `.sr` capture → frames, messages, key/rotary mapping. stdlib only |
| `src/rnse/map_buttons.py` | guided button/rotary mapping over the listener's serial output; writes `keymap.json` + `keymap.md` |
| `arduino/fuzzer/fuzzer.ino` | byte sweep with proper reset sequencing and a marker channel |
| `arduino/listener/listener.ino` | boot the board, decode messages, stream to USB; head-unit link layer (init frames, `0x15` ACK, NAK, retransmit); lighting control (`0x07` lamps, `0x06` dimmer, §8); raw frames |
| `arduino/handshake/handshake.ino` | dumb two-stage probe: reset, wait, send `STEPS[]`, observe on the LA |
| `docs/keymap.json` | the mapping in §4/§5, machine-readable |

Logic analyzer channel convention: `D0=Fuzzer`, `D1=Board`, `D2=Marker`,
`D3=Reset`.

---

## 12. Open questions

1. ~~What ends the `0x0F` announce phase?~~ **SOLVED** — sending `0x15`, and
   `0x15` specifically: `0x14` is ignored, `0x16` leads elsewhere. See §7.
2. ~~Does an ACK stop the 4× key/rotary retry, and what is its format?~~
   **SOLVED** — the bare byte `0x15`. Each report is then sent once (§6).
3. ~~Why is reply latency 1.2 ms in one state and 258 ms in another?~~
   **RESOLVED** — 258 ms is the state-B transition delay, not a latency.
4. **What reply resolves state B** (the `18 03 80 9B` broadcast)? The
   firmware says `0x16` means "ACK, a frame follows" (§7). **A valid frame
   straight after `0x16` does not help** (§7, 2026-10-10). Still untried:
   ACKing the `0x18` with `0x15`, and sending a frame after the 258 ms
   transition.
5. How large is the command space around `0x14`/`0x15`/`0x16`, and what do the
   other values do?
6. Why does the panel answer only every 2nd–3rd byte regardless of byte gap?
7. ~~Physical identity of each key bitmap bit.~~ **SOLVED** — all 18 buttons
   mapped, see §4.
8. ~~Which rotary channel is the volume knob vs the scroll wheel.~~ **SOLVED** —
   d0 = volume, d2 = scroll, bit 7 = 0 for CW. See §5.
9. What is `0x22`, and does it have its own message type? The head unit's
   firmware does not know it: it would reject `0x22` as ≥ 0x13.
10. What do status payloads `0x40` / `0x01` / `0x06` / `0x80` mean? On the
    **head-unit side** they are bit flags: `0x01` checksum, `0x04` wrong
    address, `0x40` wrong length, `0x80` no handler (`FIRMWARE.md` §5.5). If the
    panel uses the same flags, the byte sweep mostly got "wrong length", which
    is what a lone byte would cause. `0x06` would be `0x04 | 0x02`, and `0x02`
    is unknown.
11. ~~What drives the backlight?~~ **SOLVED** — the lamp frame `0x07` bit
    `0x0040` switches it, dimmer channel C sets its brightness, and connector
    pin 9 feeds it (§8). The 8-pin IC is a TA75W01FU op-amp, a rail monitor
    (§10, `BACKLIGHT.md`).
12. ~~Where does the volume-knob push (power/mute) go?~~ **SOLVED** — nowhere
    near the MCU: it shunts connector pin 7 to ground (§10).
13. Are the unused key bits (P*.0 / P*.4, bytes 3–5) dead positions in a scan
    matrix, or keys this panel variant does not populate? (§4)
14. ~~What can be sent *to* the panel?~~ **SOLVED** for what matters: the
    init sequence (§7), the lamps (`0x07`) and the dimmer (`0x06`) (§8). What
    init frames `02`, `03`, `0A` and `09` configure, and what `0x01` and `0x0E`
    do, is still unknown.
15. **What does PPG1 (connector pin 5) carry?** It is a hardware PWM output
    from the MB90561A and has never been captured. Put it on the logic analyzer
    and see whether it is idle, free-running, or modulated by anything.

---

## License

This document is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Copyright 2026 André Carvalho — [rnse project](https://github.com/RedRoserade/rns-e).
If you reuse any of it, please credit it and link back.

The protocol described here is a set of facts about how the hardware behaves and
is not covered by that license; only this description of it is.
