# RNS-E front panel — backlight and analog stage

Working notes on the 8-pin IC at connector pins 8/9, the discrete LED driver
around it, and how the backlight is switched.

Companion to `PROTOCOL.md`, which covers the serial link. This file supersedes
`PROTOCOL.md` §9 "The 8-pin IC drives the backlight" and open question 11 — see
§11 for what needs changing there.

**Status.** The driver chain is now understood end to end except for one node:
what drives the base of `TR5015`. Everything downstream of that node is
identified, and the topology is conventional throughout. The 8-pin IC turns out
not to be part of the switching path at all.

---

## 1. The 8-pin IC is a Toshiba TA75W01FU — **established**

| marking | reading |
|---|---|
| top: `5W01` | the part marking. The datasheet's *Marking (Top View)* figure shows exactly `5W01` |
| bottom: `9.9` | lot / date code. The same figure calls out a "Lot. No." field; not part of the part number |

A **dual operational amplifier** — LM358-class, not a dedicated driver IC.

| property | value |
|---|---|
| package | **SSOP8-P-0.65** — 0.65 mm pitch |
| supply | single 3–12 V, or dual ±1.5 to ±6 V |
| input CM range | 0 V to VCC − 1.5 V (includes ground) |
| output swing | 0 V to 3.4 V at VCC = 5 V — ~1.6 V of top-rail headroom |
| input bias current | 45 nA typ, 250 nA max |
| abs max VIN | −0.3 V to VCC — the inputs have clamp structures |
| supply current | 0.7 mA typ |

```
        8       7       6       5
       VCC    OUT B   IN B-   IN B+
       ┌───────────────────────────┐
       │   A: 1,2,3     B: 5,6,7   │
       └───────────────────────────┘
       OUT A   IN A-   IN A+    VEE
        1       2       3       4
```

The IC does not generate the 9 V rail; pin 8 is simply VCC.

---

## 2. Microcontroller — **established**

MB90561A in the **FPT-64P-M09** (LQFP-64) package.

| MCU pin | function |
|---|---|
| 1, 2 | P45/PPG4, P46/PPG5 |
| 3, 4 | P50/**AN0**, P51/**AN1** |
| 5–10 | P52–P57 / AN2–AN7 |
| 12, 13, 14 | AVCC, AVR, AVSS |
| 61–64 | P41/PPG0, P42/PPG1, P43/PPG2, P44/PPG3 |

P50–P57 are general-purpose I/O by default; they act as analog inputs only when
the corresponding ADER bit is set.

---

## 3. Netlist

Source of truth. Prefer editing this over the schematic in §4.

`U5001` is a placeholder; the 5W01's silkscreen designator has not been read.

### Components

| refdes | part | package | role |
|---|---|---|---|
| U5001 | TA75W01FU (`5W01`) | SSOP8-P-0.65 | dual op-amp |
| TR5006 | `FY 67`, PNP | **SOT-89** | high-side switch, all backlight LEDs |
| TR5015 | NPN | **SOT-23** | low-side driver for TR5006's base |
| R5184 | 10 kΩ | — | TR5006 base pull-up (default OFF) |
| R5100 | 470 Ω | — | TR5006 base drive |
| R5121 | 750 Ω | — | one of many LED limiting resistors |
| — | 150 Ω … 1 kΩ | — | the rest of the LED limiting resistors |
| R5236 | 4.7 kΩ | — | op-amp pin 5 divider, bottom leg |
| C? | unknown | — | TR5015 base to ground |
| — | red SMD LEDs | — | Vf ≈ 2.0 V (diode test) |

Package pin conventions, both matching the traced orientation:
SOT-89 = 1 base, 2 collector (tab), 3 emitter. SOT-23 = 1 base, 2 emitter,
3 collector.

### Nets

| net | nodes | status |
|---|---|---|
| `GND` | conn 2 · U5001 1,2,3,4 · MCU 3,4 · R5236.2 · TR5015 E · C?.2 · LED cathodes | **measured** ≤ 0.6 Ω |
| `+9V` | conn 9 · U5001 8 · TR5006 E · R5184.1 · head unit power conn pin 4 | **measured** 9.0 V |
| `N_PBASE` | R5184.2 · TR5006 B · R5100.1 | measured |
| `N_NCOLL` | R5100.2 · TR5015 C | measured |
| `N_NBASE` | TR5015 B · C?.1 · **?** | **incomplete — the last unknown, §8** |
| `N_COLL` | TR5006 C · R5121.1 · many others | measured |
| `N_INB` | U5001 5 · R5236.1 · **?** | **incomplete — §7** |
| `N_OUTB` | U5001 6 · U5001 7 · conn 8 · via → ? | measured; via untraced |

---

## 4. Schematic as understood

```
  conn 9 ──┬──────────────────────────────────┬───────────── +9.0 V
           │                                  │
           │                              ┌───┴───┐ E
      ┌────┴────────┐                   R5184     │
      │ 8 VCC       │                    10k      │  TR5006 (SOT-89, PNP)
      │             │                     │      ╱│
      │ 5 IN B+ ─┐  │                     ├─── B  │
      │ 6 IN B- ─┼──┼── 7 OUT B ──┬── conn 8       ╲│
      │ 7 OUT B ─┘  │             │      │         │ C
      │             │            via → ? │         │
      │ 1,2,3,4 GND │                    │         ├──┬── R5121 750R ──> LED ──> GND
      └─────────────┘                 R5100        │  ├── 470R…1k ─────> LED ──> GND
           │                           470R        │  ├── 150R ────> LED·LED·LED ─> GND
        R5236 4.7k                       │         │  └── … ~20 strings total
           │                             │         │
    ?? 4.7k to +9V ??                    │         │
           │                             │         │
          GND                            └─────────┴── C  TR5015 (SOT-23, NPN)
                                                    ╲│
                                          ?? DRIVE ?? ── B
                                              │        ╱│
                                             C?         │ E
                                              │         │
                                             GND       GND

           MCU pin 3 (AN0) ── GND        MCU pin 4 (AN1) ── GND
```

---

## 5. Measurement technique

Beep mode cannot distinguish a copper trace from a semiconductor path, and
bridges adjacent pins at SSOP-0.65. What made the later results trustworthy:

- **Read Ω, not beeps.** Copper is < 1 Ω. Hundreds of Ω to kΩ means you are
  reading through silicon.
- **Reverse the probes.** A copper short is symmetric; a junction is not.
- **Sharpen the probe.** 0.65 mm pitch leaves ~0.3 mm of gap; a standard DMM tip
  is several times wider.

---

## 6. Op-amp A is an unused section — **established**

Op-amp pins 1, 2, 3, 4 and MCU pins 3, 4 all measure ≤ 0.6 Ω to connector pin 2.
The whole A section is grounded, as are AN0 and AN1.

Grounding an op-amp *output* is unusual but harmless here: IN+ is also grounded,
so the output wants 0 V anyway. It reads as a deliberate "park the section"
choice, and grounding unused analog inputs is ordinary practice.

> **Correction.** An earlier revision of this file concluded from the above that
> "the MCU has no part in the backlight." That was wrong. It ruled out an
> *analog* path only. The discovery of TR5015 (§8) opens a digital one, and the
> elimination argument in §8 now says the MCU almost certainly **is** the
> control point. The original working assumption — that illumination is turned
> on by a command to the microcontroller — looks correct.

---

## 7. Op-amp B is a rail monitor, not part of the switching path

Pin 6 tied to pin 7 makes op-amp B a **unity-gain follower**, so OUT B = IN B+.
R5236 (4.7 kΩ) pulls pin 5 toward ground.

### Pin 5 is still incomplete

A follower with only a pull-down on its input outputs 0 V; the measured output
is +4.5 V. Input bias current cannot explain it (250 nA max across 4.7 kΩ is
1.2 mV). Holding pin 5 at 4.5 V requires **0.96 mA** from somewhere.

The rail is **9.0 V**, and 9.0 / 2 = **4.50 V exactly**. So `N_INB` is almost
certainly the midpoint of a **matched 4.7 k / 4.7 k divider** across the rail.
**Prediction: a second 4.7 kΩ from op-amp pin 5 to +9 V**, likely on the far
side of the board.

### Connector pin 8 carries VRAIL / 2 — **inferred**

Connector pin 9 traces at the head-unit end to **pin 4 of a power connector**,
independently confirming it is a supply rail.

If OUT B is exactly half the rail, connector pin 8 is a **rail monitor**: halved
to fit a 0–5 V ADC or comparator on the head-unit side, buffered so that loading
the cable does not disturb the divider.

That buffer is the whole reason the op-amp exists. A bare divider would be
enough to bias something on this board; you only need a follower when driving a
**cable to another board**, where the load is unknown.

Two points already sit on the line `conn 8 = conn 9 / 2`:

| conn 9 | conn 8 | when |
|---|---|---|
| 9.0 V | 4.5 V | panel attached to a working head unit |
| 0 V (floating) | 0 V | bench, rail unfed |

The 0.3 V seen on an unfed pin 9 is a floating net read by a 10 MΩ meter, not a
signal. It confirms nothing on the panel generates that rail.

**Op-amp B does not drive the transistor base.** TR5015 does (§8). So op-amp B's
only job is the monitor, which makes the whole IC a bystander to the backlight.

---

## 8. The driver chain — conventional, and nearly complete

```
  +9 V ──┬───────────────── E  TR5006 (PNP, SOT-89)
         │
      R5184 10k
         │
         ├─────────────── B  TR5006
         │
      R5100 470R
         │
         └─────────────── C  TR5015 (NPN, SOT-23)
                          E  TR5015 → GND
                          B  TR5015 → C? → GND
                                     → ?? DRIVE ??
```

This is the **standard two-transistor high-side switch**, and it is the reason
the arrangement looked wrong in isolation:

- A PNP high-side switch needs its base pulled *below* its emitter to turn on.
  Its emitter is at +9 V, so the base must be dragged toward ground — but the
  thing doing the dragging usually runs on 5 V logic and cannot tolerate 9 V.
- So you use a second, small NPN as a **level shifter**. Its emitter is at
  ground, so a 5 V logic signal can drive it directly, and its collector can
  swing all the way up to 9 V without stress.
- R5184 (10 kΩ) holds the PNP off by default. R5100 (470 Ω) is the path that
  turns it on.

Sequence: drive TR5015's base high → TR5015 saturates → its collector goes to
~0.15 V → R5100 drags the PNP base down → TR5006 turns on → all LED strings
light.

### Currents

With TR5015 saturated, the PNP base clamps at 9 − 0.7 = 8.3 V:

| quantity | value |
|---|---|
| through R5100 | (8.3 − 0.15) / 470 = **17.3 mA** |
| back through R5184 | (9 − 8.3) / 10 k = 0.07 mA |
| **TR5006 base current** | **≈ 17.2 mA** |

For a ~300 mA load that is a forced beta of about 17 — **very hard saturation**,
deliberately over-driven. Common in automotive designs where guaranteed low
Vce_sat matters more than the wasted milliamps. It also means TR5006 will run
cool, which fits the SOT-89 being chosen for current rating rather than heat.

TR5015 must sink that 17.3 mA. At hFE 100 it needs ~0.17 mA of base current, and
would normally be driven at ~1 mA for margin.

### What drives TR5015's base

`N_NBASE` currently has only a capacitor to ground, which by itself would never
turn anything on — the same shape of gap as op-amp pin 5. The capacitor is a
**noise filter**, standard in automotive so that RF pickup cannot flash the
backlight. There must be at least one more component.

**Predictions:**

- A **series base resistor** from the control source, ~2.2–10 kΩ. From a 5 V
  logic high, (5 − 0.7) / 4.3 kΩ ≈ 1 mA, so 4.7 kΩ is the value to expect.
- Possibly a **pull-down resistor** base-to-ground, guaranteeing OFF while the
  driving pin is high-impedance during reset.
- If the capacitor is large, it may also be a deliberate **soft-start**, fading
  the backlight in rather than snapping it on.

### The control source is on the panel — **inferred, by elimination**

All nine connector pins are accounted for:

| pin | signal |
|---|---|
| 1 | VCC +5 V |
| 2 | GND |
| 3 | RX |
| 4 | TX |
| 5 | PPG1 |
| 6 | reset |
| 7 | power button |
| 8 | rail monitor, VRAIL / 2 |
| 9 | +9 V LED rail |

**There is no spare pin for a backlight enable.** So whatever drives TR5015
originates on the panel itself, and the MCU is the only active device there.
That makes the MCU the control point, and implies a **serial command** for the
backlight — directly reopening `PROTOCOL.md` open question 14.

### Prime suspects: the unused PPG channels

`PROTOCOL.md` establishes that PPG1 goes out to connector pin 5. The MB90561A
has six PPG channels and the other five are unaccounted for. A PPG driving
TR5015 would give **hardware PWM brightness control** — and the capacitor on the
base is consistent with smoothing that PWM toward a DC level.

Short list to check `N_NBASE` against, on LQFP-64:

| PPG | MCU pin |
|---|---|
| PPG0 | 61 |
| PPG2 | 63 |
| PPG3 | 64 |
| PPG4 | 1 |
| PPG5 | 2 |

If it lands on a plain I/O port instead, the backlight is on/off only.

### The LED strings

The limiting resistors on `N_COLL` range **150 Ω to 1 kΩ by board position** —
per-position trimming so the panel looks evenly lit behind legends of different
size and light pipes of different length.

At a 9 V rail, collector ~8.8 V, red LEDs at Vf ≈ 2.0 V:

| R | 1 LED | 3 LEDs in series |
|---|---|---|
| 150 Ω | 45 mA — too high for a small SMD part | **19 mA** ✓ |
| 330 Ω | 21 mA | 8.5 mA |
| 750 Ω | **9.1 mA** ✓ | 3.7 mA |
| 1 kΩ | 6.8 mA | 2.8 mA |

So both resistor value *and* series depth vary by zone. Roughly 20 strings
averaging ~15 mA puts total collector current at **150–400 mA**.

### Unverified

- `FY 67` and TR5015 have not been matched to datasheets; PNP and NPN are
  inferred from the traced orientations, both of which are self-consistent.
- The capacitor on `N_NBASE` has no measured value.
- The 5W01's silkscreen refdes has not been read.

---

## 9. Test plan

**T1 — force the backlight on, bypassing the MCU entirely.** With the rail fed
(§10), **bridge TR5015's collector to its emitter**. That imitates TR5015 being
fully on and should light every string. Both pins are accessible on the SOT-23,
and the 470 Ω and 10 kΩ limit the current, so the risk is low.

This is the highest-value test in the document. It proves the whole chain works
independently of any unknown drive signal, and it tells you what "lit" looks
like before you go hunting for the command.

**T2 — trace `N_NBASE`.** The last unknown node. Check the PPG short list in §8
first. Expect a ~4.7 kΩ series resistor alongside the capacitor.

**T3 — feed the rail and check `conn 8 = conn 9 / 2`.** One probe tests both the
matched-divider prediction and the rail-monitor reading, and it works even if
nothing lights.

**T4 — find the missing resistor on op-amp pin 5.** Predicted 4.7 kΩ to +9 V,
likely on the far side of the board.

**T5 — measure the `N_NBASE` capacitor.** Small (≤ 1 nF) means plain EMI
filtering. Large (≥ 100 nF) with a 4.7 kΩ series resistor means a deliberate
soft-start ramp, or PWM smoothing.

**T6 — measure Vce across TR5006 while lit.** ~0.2 V confirms the saturated
switch reading. Volts would mean linear operation and a different design intent.

**T7 — once the backlight can be lit, sweep the serial command space again**
and watch for it changing. Only meaningful after T1 and T2.

---

## 10. Powering the rail

Feed connector pin 9, grounded to connector pin 2, alongside the existing
Arduino 5 V on pin 1.

**Feed pin 9 only. Putting 9 V on connector pin 1 would destroy the MCU.**

*No series resistor.* A resistor in series with a supply does not set a voltage;
it drops I × R, so the result depends on how much current the load happens to
draw — unpredictable for a rail whose current varies with how many LEDs are lit.
A resistor can also only lower the voltage, and 5 V is already below the 9 V
wanted.

| source | rail | notes |
|---|---|---|
| **PP3 9 V battery** | 9.0 V | the real test; ~2 Ω internal resistance is mildly self-limiting |
| USB charger / power bank | 5.0 V | safe and informative, but partial — see below |

A 5 V rail scales the whole chain down: divider midpoint 2.5 V, OUT B 2.5 V,
collector ~4.8 V. The op-amp is fine — 5 V is the datasheet's own
characterisation point.

LED forward voltage does not scale, so at 4.8 V:

| string | Vf | I = (4.8 − Vf) / 750 |
|---|---|---|
| 1 red | 2.0 V | 3.7 mA — clearly visible |
| 2 red | 4.0 V | 1.1 mA — faint, visible in a dark room |
| 3 red | 6.0 V | nothing — above the 4.8 V available |

**Expect partial illumination at 5 V and do not read it as a fault.** Three-deep
strings stay dark while single-LED zones light. Which zones light is useful data
about how the strings are grouped.

Estimated total draw:

| rail | total |
|---|---|
| 5.0 V | 50–150 mA |
| 9.0 V | 150–400 mA |

**Do not source this from the Arduino's 5 V pin.** On a USB-fed board that pin
is the USB rail behind a 500 mA polyfuse with the board already drawing from it;
150 mA of LEDs risks brownouts and resets that will look like protocol faults.
A PP3 at 300 mA will sag about half a volt and will not last long, but it is
fine for a few minutes.

---

## 11. What this changes in `PROTOCOL.md`

- §9 "The 8-pin IC drives the backlight" — the IC is a **dual op-amp** and is
  **not in the switching path at all**. The driver is TR5006, gated by TR5015.
  Op-amp A is unused; op-amp B is a rail monitor. The speculation about "a
  boosted rail with a lower-voltage control or feedback input" is resolved:
  connector pin 9 is the LED supply rail, IC pin 8 is simply VCC, and connector
  pin 8 is VRAIL / 2 going back to the head unit.
- §9 markings table — `5W01` is matched, `9.9` is a lot code.
- §9's "+8.0 V" correction — **reverted**. The rail is **9.0 V**; 8.0 V was a
  rounded earlier reading. This matters because it is what makes the matched
  4.7 k / 4.7 k divider land on exactly 4.50 V.
- §9's conclusion that no UART traffic will light the panel — **likely wrong**,
  and the reasoning has flipped twice. All nine connector pins are accounted for
  and none is a backlight enable, so control must originate on the panel, and
  the MCU is the only candidate (§8).
- Open question 11 "what part is it" — **SOLVED**, TA75W01FU.
- Open question 14 — **reopened and narrowed**. There probably *is* a command;
  find what drives `N_NBASE` first, then sweep.
- Open question 15 (PPG1) — related. Five PPG channels are unaccounted for and
  one of them may be the backlight PWM.

See also [`CANBUS.md`](CANBUS.md), which takes the §8 conclusion — that the
command must originate at the MCU — and plans how to make a head unit issue it,
using the vehicle CAN bus as the stimulus. Its §2 transcribes the head unit's
connector legend, which shows **no illumination pin on any connector** and so
closes off the last non-serial explanation.

---

## 12. Open questions

1. What drives `N_NBASE`? Check the PPG short list in §8. (T2)
2. Does the chain light when TR5015 is bypassed? (T1)
3. What feeds op-amp pin 5? Predicted 4.7 kΩ to +9 V. (T4)
4. Is the backlight on/off, or PWM-dimmable via a PPG channel? (T2, T5)
5. Where does the `N_OUTB` via go, given OUT B is not the base driver?
6. Is there a serial command for the backlight? (T7) — **supported by
   behaviour, still unobserved.** A head unit powered on the bench with no CAN
   boots to its PIN screen while the panel, attached and with its +9 V rail
   live, stays dark. So the MCU does not light the backlight on its own
   initiative; it is waiting for something. See `CANBUS.md` §3.
7. What are `FY 67` and TR5015, and is the 5W01's refdes readable?

---

## License

This document is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Copyright 2026 André Carvalho — [rnse project](https://github.com/RedRoserade/rns-e).
If you reuse any of it, please credit it and link back.

The hardware described here is a set of facts about how the circuit behaves and
is not covered by that license; only this description of it is.
