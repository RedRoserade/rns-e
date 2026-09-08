# RNS-E head unit — driving it over CAN to find the backlight command

A plan for using the vehicle CAN bus to make a head unit command the front
panel, so the other half of the protocol can be observed rather than guessed.

Companion to `PROTOCOL.md` (the panel serial link) and `BACKLIGHT.md` (the LED
driver chain). Where those two describe measurements, **this file describes an
experiment that has not been run yet.**

**Status. The experiment in §6 has not been run.** What *is* measured: the
connector legend in §2, read off the unit's own case; the panel backlight
staying dark on a no-CAN power-up in §3; and the 30-minute shutdown in §5. Note
that §5 and part of §3 were observed **before** the unit was bricked, and say
nothing about its current state — §5 is explicit about what that costs.
Everything about CAN message *content* — the rest of §3, and §4 — is third-party
and ungraded by any measurement here. Claims are marked individually; treat
anything not marked **established** as a hypothesis. Hardware for §6 is listed
in `HARDWARE.md`.

---

## 1. Why the head unit is the missing instrument

`PROTOCOL.md` open question 14 is the largest gap in the project:

> **Nothing has ever been sent *to* the display.** Every message decoded so far
> travels panel → head unit.

That is not because the head unit sends nothing. It is because every capture so
far was taken with the panel driven by an Arduino, and the Arduino only knows
the commands we have already guessed. The head unit knows all of them.

`BACKLIGHT.md` §8 narrowed this further. All nine connector pins are accounted
for and none is a backlight enable, so whatever drives `N_NBASE` originates on
the panel, and the MCU is the only active device there — which means there is
almost certainly a **serial command** for the backlight. We have never seen it
because we have never had anything on the wire that would send it.

A powered head unit is that thing. The problem reduces to: **make a head unit
change the panel illumination on demand, and watch the wire while it does.**

On a bench, the lever for that is CAN.

---

## 2. The connector — **established**

Read directly from the label printed on the head unit itself:
[`rns-e-pinout.png`](rns-e-pinout.png). This is the strongest class of evidence
in the project — not a forum diagram, not an inference, but the manufacturer's
own legend on the case.

| field | value |
|---|---|
| part number | `8E0 035 192 Q` |
| maker | Aisin AW Co., Ltd., Belgium |
| built | 05/03/2007 |
| supply | `12V D.C. NEGATIVE GND.` |
| internal fuse | `FUSE 15A` |
| other markings | `H73`, `0550`, `02S`, `86113-60V330`, `MON AN1 0003` |

**Note the part number.** `8E0` is the A4 B7 family; `README.md` records the
reverse-engineered panel as `8P0 035 192 H`, an A3 8P part. Both are **192**
series, so the panel protocol is expected to carry across — but if these two
boards are used together on the bench, that is *itself* the cross-variant test
`README.md` flags as unconfirmed, and any difference found is a result, not a
fault. Confirm which boards are actually in play before reading anything into a
mismatch.

### D — power connector — **established**

| pin | signal | direction |
|---|---|---|
| 9 | **CAN-H** | bidirectional |
| 10 | **CAN-L** | bidirectional |
| 11 | TEL-MUTE | input |
| 12 | **KL. 31** — ground | — |
| 13 | U14 St DSP (Radio On) | **output** — amp / DSP turn-on |
| 14 | DWA-GND — alarm ground | — |
| 15 | **KL. 30** — permanent +12 V | input |
| 16 | U14R-1 | — |

Bench minimum is therefore **D15, D12, and the CAN pair on D9 / D10**.

### What is *not* on the connector — the important part

Two absences, both load-bearing:

**There is no KL. 15.** The power connector has permanent +12 V and ground and
nothing else in the supply category. `U14 St DSP (Radio On)` on D13 is an
*output* — it is how the head unit turns an external amplifier on, not how the
car turns the head unit on. So there is no ignition line to raise on the bench.

> **Correction.** An earlier revision of this file listed D13 as a "radio-on /
> switched supply" to be fed alongside D15, following a forum summary. That was
> wrong, and feeding it would have been driving into an output. The label
> settles it.

**But the unit still wakes without one — from the panel.** Observed on the
bench: with permanent 12 V and ground only and no CAN whatsoever, **pressing the
power button turns the unit on.**

That is consistent with the rest of the project. `PROTOCOL.md` §9 establishes
that the power/mute button is not connected to the panel MCU at all — it shunts
**panel connector pin 7 to ground**, and the head unit senses it directly. So the
head unit's wake input is a switch closure on a pin already broken out on the
bench, and it can be asserted with a wire.

> **Correction.** An earlier revision of this file reasoned from "no KL. 15 pin"
> to "CAN is the only wake path that exists," and `HARDWARE.md` promoted the CAN
> adapter to *required* on that basis. Both were wrong. The absence of KL. 15 is
> real; the conclusion drawn from it was not, because it treated the connector
> legend as the complete list of inputs and forgot the panel is also an input.
> CAN is needed to keep the unit awake (§5), not to wake it.

**There is no illumination or dimmer pin, on any connector.** Not on D, not on
the A speaker block, not on either of the B/C external control blocks, not on
the 32-pin AMP connector. The full transcription is in §2.1; nothing in it
carries a dimming signal.

This is the same shape of argument as `BACKLIGHT.md` §8, and it lands the same
way. Every pin is accounted for and none of them is illumination, so **dimming
can only arrive over CAN.** That upgrades §3 from "a third-party report about
`0x635`" to "a third-party report about `0x635`, which is now the only category
of mechanism left." It is still possible that `0x635` is the wrong identifier;
it is no longer possible that the answer is a wire.

By the same token it constrains §5's list of failure modes: a unit that never
initialises CAN cannot be woken *or* dimmed by any other route, so T4 becomes
the pivotal observation rather than merely a preliminary one.

### K-Line on B5 — an unrelated but valuable find

`B5 K-Line` is the ISO 9141 diagnostic line. It is not part of this experiment,
but it is a **second, independent channel into the bricked unit** — the one a
dealer tool would use, and the one that would carry fault codes or a reflash if
either is possible. Worth pursuing on its own track with a KKL / VAG-COM
interface, and worth knowing about before deciding the bricked unit is scrap.

### 2.1 Full label transcription

Kept as text so it is searchable and survives the photo being unreadable.

**A — speaker connector**

| pin | signal | | pin | signal |
|---|---|---|---|---|
| 1 | N.C. | | 5 | N.C. |
| 2 | RIGHT FRONT (+) | | 6 | RIGHT FRONT (−) |
| 3 | LEFT FRONT (+) | | 7 | LEFT FRONT (−) |
| 4 | N.C. | | 8 | N.C. |

**B — ext control connector**

| pin | signal | | pin | signal |
|---|---|---|---|---|
| 1 | N.C. | | 7 | BOSE Pin |
| 2 | CDC-NF GND | | 8 | CDC-NF L In |
| 3 | V-Signal | | 9 | CDC-NF R In |
| 4 | U14R-2 | | 10 | U14 ST CDC |
| 5 | **K-Line** | | 11 | CDC-Data In |
| 6 | CDC-Data OUT | | 12 | CDC-Data CLK |

**C — ext control connector**

| pin | signal | | pin | signal |
|---|---|---|---|---|
| 1 | Mic In (−) | | 7 | Mic In (+) |
| 2 | RFSL | | 8 | Line Out GND |
| 3 | Line Out FL | | 9 | Line Out FR |
| 4 | Mic Out (−) | | 10 | Mic Out (+) |
| 5 | Line Out RL | | 11 | Line Out RR |
| 6 | TEL NF In (−) | | 12 | TEL NF In (+) |

**D — power connector** — see above.

**32-pin AMP connector** — pins 1–14, 16–21 and 23–28 are `N.C.` except as
listed:

| pin | signal | | pin | signal |
|---|---|---|---|---|
| 6 | AUX-NF-In-Right | | 22 | AUX-NF-In-Left |
| 13 | NF-In-Right | | 28 | NF-In-GND |
| 14 | SHIELD GND | | 29 | NF-In-Left |
| 15 | In-sync | | 30 | RGBS-In-GND |
| 16 | In-G | | 31 | In-B |
| 21 | AUX-NF-GND | | 32 | In-R |

The RGB and sync pins are the video input path — the same connector the
navigation display feed uses, and the one third-party video interfaces target.
Not relevant here, recorded for completeness.

### 2.2 The bus — bitrate still **third-party, unverified**

The connector is settled; the signalling on it is not.

| property | value | source |
|---|---|---|
| physical | CAN-H on D9, CAN-L on D10 | **label — established** |
| bus | infotainment / comfort CAN | VAG PQ platform convention |
| bitrate | **100 kbit/s** | `noobychris/audi-can-rpi` sets `bitrate=100000`; PQ platform docs |
| frame format | standard 11-bit identifiers, not extended | both reference scripts use `extended=False` |

Note that the powertrain CAN on the same platform runs at **500 kbit/s**. Some
published bench examples use 500k and report the radio ignoring them; that is a
plausible explanation for at least one of the failed attempts in the wild.

`peetereczek/openauto-audi-api` constructs its bus with no bitrate at all
(`can.interface.Bus(can_interface, bustype='socketcan')`), relying on the
interface having been configured by `ip link` beforehand. Do not copy that call
as evidence of a bitrate; it carries none.

Termination is unknown. Measure across D9 / D10 with the unit unpowered: ~120 Ω
means the unit terminates the bus and only the adapter end needs a resistor.

---

## 3. Illumination

### The panel backlight is off with no CAN — **established**

Observed on the bench, on a unit with 12 V and ground only and no CAN
whatsoever:

- the power button turns the head unit on;
- it boots as far as **rendering the PIN entry screen**, so the display and its
  own backlight are working and the application layer is running;
- **the front-panel button backlight stays dark.**

The panel was necessarily attached — the power button is on it — and the head
unit sources the panel's +9 V LED rail, so this is not a panel that was
unpowered. It was fully powered, with its LED rail live, and it stayed dark.

That is a clean negative, and it is the most useful single observation in this
document:

- the backlight is **not a boot-time default-on**, so it is not simply enabled
  by the rail coming up;
- the panel MCU does not light it on its own initiative, which supports
  `BACKLIGHT.md` §8 — the drive to `N_NBASE` is waiting for something;
- combined with §2 (no illumination pin on any connector), the something has to
  arrive over a channel that exists. The panel link cannot be the origin, since
  the head unit is the master there. K-Line is a diagnostic channel, not a
  runtime one. **That leaves CAN.**

It also answers what T3 was going to ask, without the CAN rig.

### The confound — worth naming

The unit was sitting at a **PIN entry screen**, i.e. locked. A locked head unit
that withholds illumination until it is unlocked would produce exactly the same
observation, for a completely different reason.

This does not overturn the conclusion — the elimination argument in §2 stands on
its own and is unaffected by lock state — but it does mean the negative is not
clean, and the CAN-origin claim rests more on the elimination than on this
observation. **T3b resolves it for the cost of typing four digits.**

### `0x635` — the illumination message — **third-party, unverified**

The single most useful identifier for this project.

```
ID   0x635
DLC  3
[0]  display backlight   0x00 (dimmest) .. 0x64 (brightest)
[1]  button backlight    0x00 (dimmest) .. 0x64 (brightest)
[2]  unknown
```

Reported values in the wild include `00 FF 00` for "lights on" and a leading
`0x00` for "lights off"; the `0xFF` sits outside the stated `0x00..0x64` range,
so either the range or that example is wrong. Establishing which is one of the
outcomes of §6.

**Byte 1 is the front-panel button backlight.** That is the far end of TR5006,
TR5015 and `N_NBASE`. If the head unit acts on that byte at all, then between
receiving it and the LEDs changing there is a serial frame on the 9-pin
connector that nothing in this project has ever seen.

`0x635` also appears in the `can_filters` list of `noobychris/audi-can-rpi`,
which is weak corroboration that the ID exists on this bus on a car of this era
— that script only receives, and never decodes it.

Note what is and is not established. **That illumination arrives over CAN** is
now well supported: by elimination from the connector legend, and by a booted
unit leaving the panel dark. **That `0x635` is the identifier** is still a
third-party claim and remains untested here.

---

## 4. Keeping the unit awake — **third-party, unverified**

| ID | DLC | payload | meaning | period |
|---|---|---|---|---|
| `0x271` | 2 | `01 80` | terminal 15 / ignition on | 100 ms |

Both reference scripts read `0x271` and treat it as the ignition and key-pull
signal, so the identifier is well attested even though the exact payload is not.

**This is not how you turn the unit on** — the power button does that (§2). What
`0x271` and the frames around it are for is *keeping* it on, and telling it a
car is present. See §5: the unit powers up happily and then shuts itself down
again on a timer.

**Expect this to be insufficient on its own.** At least one published attempt
reports a radio that ignored `0x271` + `0x635` entirely. A real car presents a
gateway and a continuous background of traffic; a unit that cross-checks several
sources before leaving standby will see two lonely identifiers as an incomplete
picture.

Fallback: transmit the whole receive-filter set from `noobychris/audi-can-rpi`
as periodic frames, on the theory that a script written against a real car
filtered for the identifiers that were actually present.

```
0x271 0x2C3 0x351 0x353 0x35B 0x461 0x5C0 0x5C3 0x602 0x623 0x635 0x65F 0x661
```

Known or claimed meanings, from `peetereczek/openauto-audi-api`:

| ID | meaning |
|---|---|
| `0x271` | ignition, key pull |
| `0x351` | reverse gear |
| `0x461` | RNS-E button controls |
| `0x5C3` | multi-function steering wheel buttons |
| `0x623` | date / time from the driver information system |
| `0x65F` | car model and year |
| `0x661` | RNS-E TV mode status |

`0x461` is worth noting for a different reason: it is described as *RNS-E button
controls*, i.e. traffic in the same functional area as this project but on the
vehicle side of the head unit. It is not the panel link, but it may share
vocabulary with it.

---

## 5. The 30-minute shutdown — and what it does *not* tell us

**With 12 V and ground only and no CAN present, the unit switches itself off
after about 30 minutes.** This is battery-protection behaviour, and it is
correct behaviour: a head unit left awake on a parked car flattens it.

### Provenance — read this before using it

This was observed **while the unit was still working**, before the failed
software update. It is therefore a fact about how an `8E0 035 192` behaves, not
a fact about the state of the unit as it exists now.

> **Correction.** An earlier revision of this section read the power-on and the
> shutdown as current, post-brick behaviour and concluded that "the brick is
> much more alive than assumed" — that most of the firmware must be working and
> the damage was probably confined to the navigation or application layer. That
> inference was built on a misreading of when the observation was made, and it
> is withdrawn. `HARDWARE.md` was corrected in the same way: the donor head unit
> is **not** demoted to a fallback on this evidence.

The practical consequence: **the go/no-go on the bricked unit has not been
run.** T2 still has to happen, and its result is genuinely unknown. Everything
from T4 onward is contingent on it.

What the observation *is* good for is designing the experiment, which is what
the rest of this section does. A behaviour reproducible on a working unit of
this part number is exactly what a test needs to be built against.

### The attribution is not established either

The shutdown is naturally read as "30 minutes without CAN activity, therefore
battery protection." That reading is probably right, but it is **not what was
observed**.

CAN has never been present on this bench. So "30 minutes with no CAN" and
"30 minutes since power-on" are, so far, the same experiment. A plain idle timer
that fires regardless of bus traffic would produce an identical result.

Which it is has a direct consequence: if the timeout is CAN-gated, traffic keeps
the unit awake and the bench session becomes unlimited. If it is a plain idle
timer, every session is capped at 30 minutes and the sweep in T6 has to be
planned around a shutdown.

### The shutdown is a free instrument

The timeout turns the unit into a **CAN presence detector**, and a far better
one than hoping for a visible response to `0x271`.

The problem with a naive wake test — "send `0x271`, look for any change in
behaviour" — is that the null result is ambiguous. Nothing visibly happening
could mean wrong bitrate, wrong pins, wrong identifier, wrong payload, or a unit
that received the frame perfectly and simply had nothing to do about it.

The timeout removes that ambiguity, because the unit reports its own verdict:

- **it stays on past 30 minutes** → the unit received and acted on your traffic.
  Bitrate, wiring, pinout, termination and the CAN controller are all confirmed
  in one binary observation, with no dependence on any identifier being correct;
- **it shuts down anyway** → either nothing reached it, or the timer is not
  CAN-gated. T4 (listening) separates those.

The cost is patience rather than money, and it validates the entire physical
layer before a single hypothesis about message content is tested.

This test assumes the bricked unit still exhibits the behaviour at all. If T2
shows it does not — no power-up, or no orderly shutdown — the instrument is
gone and a donor unit becomes the path.

### A practical note

**Until the timeout is defeated, every bench session is 30 minutes long.** T6 is
a 101-step sweep. Get T5 working first.

---

## 6. Test plan

Ordered so that each step is a go/no-go for the more expensive step after it.

**T1 — establish the panel-side baseline, no head unit.** Run the existing
Arduino setup with the +9 V rail fed per `BACKLIGHT.md` §10, and confirm the
panel boots, reports keys, and that the backlight is *off*. This is the control
condition. Without it, "the backlight came on" is not attributable to anything.

**T2 — power the head unit and press the power button.** D15 and D12 only —
there is no ignition line to raise (§2) — current-limited, on a supply with a
current readout. Record the draw from cold, through the button press, and out
to the 30-minute shutdown.

**This is the go/no-go on the bricked unit, and it has not been run.** The
power-on and shutdown behaviour in §5 was observed *before* the failed update,
so it describes a working `8E0 035 192`, not this one. Whether the brick still
powers up from the button, still reaches the PIN screen, and still shuts down in
an orderly way at 30 minutes is genuinely unknown, and everything from T4 onward
depends on the answer.

Log the standby current, the running current, the shape of the turn-on
transient, and the exact time to shutdown — a repeatable 30:00 suggests a
designed timer, a scattered figure suggests something else.

The current readout matters because the head unit generates the panel's +9 V rail — `BACKLIGHT.md`
traces connector pin 9 to pin 4 of the head unit power connector — so the
150–400 mA backlight load appears in the head unit's own supply current. The
current trace therefore reports on both liveness and illumination:

| observation | reading |
|---|---|
| stable draw, settles after a few seconds | the unit is executing something |
| sawtooth / repeating steps | boot loop — it is not going to reach the illumination task |
| near zero, or immediate rise into the current limit | dead or shorted; stop |
| a step of 150–400 mA appearing at any point | **the backlight just came on** |
| powers up, renders a screen, shuts down near 30 min | the brick behaves as the working unit did — proceed |

**T3 — capture the panel link during a no-CAN power-up.** The *outcome* of this
step is already known — §3, the backlight stays dark — but the **wire has never
been watched while it happened**, and that is the part that matters. This is the
first opportunity to record the real head-unit-to-panel conversation, and it
needs no CAN work at all.

Capture panel TX *and* panel RX from before the button press through to the
PIN screen. The interesting direction is the one never recorded. Even if no
backlight command appears — and per §3 it should not, since the backlight does
not light — the boot handshake, and any acknowledgement of key and rotary
traffic, will be in that capture. See §9.

**T3b — enter the PIN.** If the code is known, unlock the unit and see whether
the backlight comes on. This separates "no CAN dimmer command" from "unit is
locked and withholding illumination" (§3), and it costs nothing.

- backlight comes on when unlocked → the negative in §3 was about lock state,
  not about CAN, and §3's observation stops being evidence for anything;
- backlight still dark when unlocked → the negative is clean, and the CAN-origin
  conclusion is supported by observation as well as by elimination.

Either way, capture the link across the unlock. A unit transitioning from locked
to operating is a unit doing initialisation, and initialisation is where
commands live.

**T4 — verify the bus before transmitting.** `candump can0` at 100 kbit/s with
the head unit powered. A unit that transmits anything confirms the bitrate, the
wiring and the pinout in one observation, and confirms its CAN controller is
alive. **Listen before you transmit**; a transmitting node on a misconfigured
bitrate produces error frames, not silence.

**T5 — defeat the 30-minute shutdown.** Power on with the button, then transmit
`0x271` = `01 80` at 100 ms and wait it out. If the unit shuts down anyway,
escalate to the full periodic set from §4 and repeat.

**Success criterion: the unit is still on at 35 minutes.** This is the best test
in the document that costs nothing but time. It is binary, it needs no
identifier to be correct, and passing it confirms bitrate, wiring, pinout,
termination and the unit's CAN controller in a single observation — see §5.

Failing it is informative too, but only in combination with T4: silence on the
bus *and* a shutdown means nothing reached the unit; traffic on the bus *and* a
shutdown means the timer is not CAN-gated and every session is capped at 30
minutes regardless.

Once it passes, the bench session is unlimited and T6 becomes practical.

**T6 — the experiment. Sweep `0x635` byte 1** from `0x00` to `0x64` while
capturing the panel link, holding byte 0 constant. Then sweep byte 0 with byte 1
held, to separate display backlight from button backlight. Then try `0xFF` on
both, to settle the range question in §3.

**T7 — dwell at the extremes.** Hold `0x635` byte 1 at `0x00` for a minute, then
at `0x64` for a minute. A command sent only on change looks like a transient in
a sweep; a command re-sent periodically shows up in the dwell. Both patterns
have precedent in `PROTOCOL.md` — the panel is edge-driven, but the boot
announcement is periodic.

**T8 — cross-check against `N_NBASE`.** Whatever T6 produces, confirm it at the
transistor: put a probe on TR5015's base while the sweep runs. This distinguishes
"the head unit sent a frame" from "the frame did what we think it did", and it
answers `BACKLIGHT.md` open question 4 — a DC level that tracks the sweep means
PWM smoothed by the base capacitor, a clean two-state edge means on/off only.

---

## 7. Reading the outcome

The value of T6 is that every outcome is informative, including the null ones.

| observed | conclusion |
|---|---|
| new frame on panel RX, payload tracks the sweep | **the backlight command, found.** `PROTOCOL.md` open question 14 falls, and the payload tells you whether it is graded or binary |
| new frame on panel RX, same payload at every level | on/off only; the head unit is thresholding, and the panel has no brightness control |
| LEDs track the sweep but panel RX stays silent | the elimination argument in `BACKLIGHT.md` §8 is **wrong**. There is a path to `N_NBASE` that does not come from the MCU, and the connector pinout is incomplete |
| nothing changes anywhere, unit otherwise alive | either `0x635` is not this unit's illumination ID, or the brick has taken the illumination task with it. T3's no-CAN default says which is more likely |
| T5 failed — unit still shuts down at 30 min | do not run T6 yet. Either nothing is reaching the unit, or the timer is not CAN-gated; T4 says which, and the first case invalidates any T6 null result |

The third row is the one to watch for. It would be an unwelcome result, but it
is a clean falsification of a chain of reasoning that has already flipped twice
in `BACKLIGHT.md` §11, and it is much better found by measurement than by
another round of tracing.

---

## 8. Correlating the two buses

The experiment produces two timestamped streams that have to be lined up: CAN
frames transmitted by the host, and UART frames on the panel link. Doing this by
eye across a logic analyzer capture and a terminal log does not scale past a few
attempts, and the sweep in T6 is 101 steps.

The workable arrangement is to have **one host do both**:

- transmit the sweep and log it with `candump -tA` absolute timestamps;
- receive the panel link from a passive sniffer that timestamps each frame and
  streams it over USB;
- merge on host clock.

A single-channel bit-banged UART cannot watch both directions at once, which
matters here because the direction of interest — head unit → panel — is the one
never captured. Two hardware UARTs are wanted. `HARDWARE.md` covers this.

The logic analyzer stays the instrument for the bit-level questions (T8, and
anything that looks like a framing anomaly), not for the routine sweeps.

**Capture rate still applies**: ≥ 500 kHz, ideally 1 MHz. `README.md` documents
why 20 kHz silently corrupts data bits 5–7 at 9600 baud.

---

## 9. What this would change elsewhere

If T6 lands:

- `PROTOCOL.md` open question 14 — the whole head-unit-to-panel direction —
  opens up. The backlight command is one frame, but the capture that contains it
  contains everything else the head unit says during boot as well.
- `PROTOCOL.md` open question 2 (the ACK) may fall out of the same capture. If
  the head unit acknowledges key and rotary messages, T3 records it, and the 4×
  retry hypothesis is settled by observation rather than by the guessed ACK in
  `listener.ino`.
- `PROTOCOL.md` open question 4 (what resolves state B) likewise: a real head
  unit performs the real boot handshake, including whatever `0x16` leads to.
- `BACKLIGHT.md` open questions 4 and 6 are answered directly.

This is the argument for doing the CAN work even though `BACKLIGHT.md` T1 and T2
can establish the driver chain without it. CAN does not just answer the
backlight question; it puts a fluent speaker of the protocol on the wire.

---

## 10. Open questions

Reordered after the bench observations in §3 and §5.

1. ~~Did the panel backlight light when the unit was powered on by the button
   with no CAN present?~~ **ANSWERED — no.** The unit booted to the PIN entry
   screen with the panel attached and powered, and the button backlight stayed
   dark. See §3. Caveat in the next question.
2. **Is that negative about CAN, or about the lock state?** The unit was at a
   PIN prompt. A locked unit withholding illumination looks identical from
   outside. (§3, T3b)
3. **Does the bricked unit still do any of this?** Every behaviour in §5 was
   recorded before the failed update. The go/no-go has not been run. (T2)
4. **Is the 30-minute shutdown CAN-gated, or a plain idle timer?** Not yet
   distinguishable: CAN has never been present on this bench, so "30 minutes
   without traffic" and "30 minutes since power-on" are the same experiment so
   far. (§5, T5)
5. **Does the unit answer on K-Line (B5)?** Independent of everything else here,
   and the only other channel into it. (§2)
6. What is the standby current, the running current, and is the time to
   shutdown repeatable to the minute? (T2)
7. What is the minimum set of periodic frames that keeps the unit awake? (T5)
8. Does the unit terminate the CAN bus internally? Measure D9 / D10 unpowered.
9. Is `0x635` the correct identifier for this unit's illumination, and is byte 1
   really the button backlight? (T6)
10. Is the value range `0x00..0x64`, or does `0xFF` mean something? (T6)
11. Is the backlight command graded or binary? (T6, T8)
12. What does the head unit say to the panel during boot, and does it
    acknowledge key and rotary messages? (T3)
13. Is `0x461` — "RNS-E button controls" on the vehicle bus — related in any way
    to the `0x0C` key bitmap on the panel link, or merely adjacent?

---

## License

This document is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Copyright 2026 André Carvalho — [rnse project](https://github.com/RedRoserade/rns-e).
If you reuse any of it, please credit it and link back.

Third-party CAN identifiers referenced here are facts about how the vehicle bus
behaves and are not covered by that license; only this description of them is.

Sources consulted for the third-party claims in §2, §3 and §4:

- [`noobychris/audi-can-rpi`](https://github.com/noobychris/audi-can-rpi/blob/main/scripts/read_from_canbus.py) — bitrate, receive-filter identifier set
- [`peetereczek/openauto-audi-api`](https://github.com/peetereczek/openauto-audi-api/blob/develop/read_from_canbus.py) — identifier meanings
- [VAG CAN information, Autosport Labs forum](https://forum.autosportlabs.com/viewtopic.php?t=5581) — `0x635` byte layout and range
- [Trying to simulate ignition, `AugustoS97/CanBus-Radio-VAG` issue 1](https://github.com/AugustoS97/CanBus-Radio-VAG/issues/1) — PQ bitrates, `0x271` payload, and a report of the approach failing
- [`alphaw1n/audi-can-bus`](https://github.com/alphaw1n/audi-can-bus/blob/master/can_cmd.h) — identifier corroboration
- [RNS-E quadlock pinout](https://studylib.net/doc/18873693/rns-e-installation---close-up-of-quadlock-connector) — **superseded.** §2 now comes from the unit's own label ([`rns-e-pinout.png`](rns-e-pinout.png)), which corrected this source on D13
