# Bench hardware — what to buy, and what not to

The shopping list behind `CANBUS.md`, plus notes on sourcing a second head unit
to sniff.

Nothing here is an endorsement and no prices are quoted precisely — they are
order-of-magnitude figures in EUR as of early 2026, for the second-hand and
hobbyist-import market this work lives in.

**Read [§1](#1-do-this-first) before buying anything.** Two of the highest-value
experiments in the project cost nothing.

---

## 1. Do this first

`BACKLIGHT.md` T1 and T2 need no purchases and answer more than the CAN rig
does:

- **T1** — bridge TR5015's collector to its emitter with the +9 V rail fed. If
  every string lights, the driver chain is proven end to end and the only
  remaining unknown is the command. If it does not, the CAN work is pointless
  until you find out why.
- **T2** — trace `N_NBASE`. This is the last unknown node in the entire circuit.
  CAN cannot help with it.

If the budget is small, the probing kit in §6 beats the CAN rig in §2, because
it unblocks T2 and T2 is what is actually stuck.

---

## 2. Essential

| item | what to get | ~cost | why this one |
|---|---|---|---|
| **USB-CAN adapter** | CANable 2.0, **isolated variant**, flashed with candleLight (gs_usb). Alternative: Innomaker USB-CAN-ISO | 30–45 | Enumerates as a native SocketCAN device, so `ip link set can0 up type can bitrate 100000` and then `candump` / `cansend` / `python-can` work exactly as both reference scripts expect. No translation layer to debug while you are also debugging a head unit. |
| **Bench PSU** | Adjustable, **13.8 V**, ≥ 5 A, current limit, **current readout**. Korad KA3005P or Riden RD6006 class | 60–110 | See §3 — this is the instrument, not just the supply. |
| **Quadlock plug with pigtail** | Male quadlock for RNS-E, flying leads | ~10 | You will re-seat this many times. Stabbing wires into connector cavities damages the contacts on a unit you intend to resell. |
| **Inline fuse holder + blade fuses** | 3–5 A for bench use | ~5 | See below on rating. |
| **KKL / VAG-COM K-Line interface** | any USB KKL cable | 10–20 | Optional, but see §7 — the label shows a K-Line pin, which is a second way into the bricked unit |
| ~~**2× 120 Ω resistors**~~ | — | — | **Do not fit.** The bus turned out to be low-speed fault-tolerant CAN, and 120 Ω across the pair stops all communication (`CANBUS.md` §2.2). Leave the CANable's on-board 120 Ω jumper **open** too. For a permanent bench, use a low-speed transceiver (TJA1055 class) instead of the adapter's high-speed one. |

### Only four wires are needed

`CANBUS.md` §2 transcribes the connector legend printed on the unit. The bench
minimum is smaller than expected:

| pin | signal |
|---|---|
| D15 | KL. 30 — permanent +12 V |
| D12 | KL. 31 — ground |
| D9 | CAN-H |
| D10 | CAN-L |

**There is no ignition pin**, but you do not need one. The power connector
carries permanent 12 V and ground and nothing else in the supply category;
`U14 St DSP (Radio On)` on D13 is an *output* that turns an external amplifier
on. The unit is woken instead from the **panel** — the power/mute button shunts
panel connector pin 7 to ground and the head unit senses it directly, so a wire
on a pin you already have broken out is enough. Confirmed on the bench.

What CAN is for is *keeping* it awake, and — the whole point of the project —
lighting the panel. A unit powered this way boots as far as the PIN entry screen
with the **panel backlight still dark**, which is the observation the CAN
hypothesis rests on (`CANBUS.md` §3).

With no bus traffic the unit also shuts itself down after about 30 minutes, so
every bench session is capped at half an hour until that is defeated. See
`CANBUS.md` §5 — that timeout is the cheapest and most conclusive test of the
whole CAN setup, because the unit reports its own verdict on whether your
traffic reached it.

> **Correction.** An earlier revision of this file promoted the CAN adapter from
> "recommended" to "required" on the grounds that nothing else could wake the
> unit. That was wrong — it read the connector legend as the complete list of
> inputs and forgot the panel is one. The adapter is still the right purchase,
> for the reason above.

### Fuse rating

The label reads `FUSE 15A`, so the unit's own protection is 15 A and an inline
15 A fuse merely duplicates it. With no speakers connected the bench draw is a
small fraction of that, so fit **3–5 A** deliberately: a fuse that only matches
the device protects the device, while one sized to the actual bench load
protects against the wiring mistake you are actually likely to make.

The bench supply's current limit remains the primary protection; the fuse is
there for the case where the supply is not the thing that failed.

### Get the isolated adapter

The bench has three grounds that want to be the same and are not guaranteed to
be: the PSU (bonded to mains earth), the laptop (bonded to mains earth when
charging), and the head unit chassis. Galvanic isolation on the CAN adapter
removes the loop for about 10–15 EUR over the non-isolated version. On a bench
where the expensive, irreplaceable item is the thing under test, take it.

### Avoid

- **The CH340 "USB-CAN Analyzer" blue box.** Proprietary Windows tooling,
  inconsistent slcan implementations across clones. You will spend the money you
  saved on debugging the adapter instead of the head unit.
- **500 kbit/s-only or CAN-FD-only interfaces.** You need 100 kbit/s. Almost
  everything supports it, but check.

### Cheaper fallback

An **MCP2515 + TJA1050 module** on the Arduino you already have is about 5 EUR
and could be built this week. It works. What you lose is SocketCAN, `candump`
absolute timestamps, and drop-in reuse of both reference scripts — which matters
because `CANBUS.md` §8 depends on one host timestamping both buses against one
clock. Treat it as a probe for T4, not as the setup for T6.

---

## 3. The power supply is an instrument

This is the one place where the existing ATX-and-molex rig should be replaced
rather than extended. The ATX rail and the 4-pin molex are comfortably rated for
the load; that is not the problem. The problem is that it tells you nothing.

Three reasons for a bench supply:

1. **13.8 V, not 12.0 V.** That is what a running car presents. The unit is
   specified across roughly 9–16 V so 12 V is unlikely to be the fault, but when
   you are debugging a bricked unit you want to remove variables, not add them.
2. **Current limiting.** Set it just above expected draw. A wiring mistake then
   ends in a limited supply rather than in a dead head unit.
3. **Current draw is your only telemetry on a bricked unit.** This is the real
   argument. `BACKLIGHT.md` traces the panel's +9 V rail (connector pin 9) back
   to pin 4 of the head unit's power connector, so **the head unit sources the
   backlight current**. The 150–400 mA the LEDs draw therefore appears in the
   head unit's own supply current — which makes the PSU's ammeter a backlight
   detector that works even with the panel face-down on the bench, and a boot
   monitor that distinguishes "executing" from "boot loop" without any bus
   access at all. `CANBUS.md` T2 is built entirely on this.

A 13.8 V amateur-radio PSU plus a separate current meter is a workable
substitute if you already own one. The adjustable lab supply is better because
the current limit and the readout are the same instrument.

---

## 4. The tap harness

You need the panel connected to the head unit *and* the nine conductors brought
somewhere a probe can reach. The tap must be **passive and reversible** — no
soldering to either board — because both boards are going back together.

- **Molex PicoBlade, 1.25 mm, 9 circuits.** Buy two pre-made double-ended 9-pin
  cables, cut one in the middle, and land the conductors on a scrap of perfboard
  with 0.1 in headers. ~5 EUR.
- **Crimping it yourself is a trap at this pitch.** If you insist: housing
  `51021-0900`, terminals `50079-8100`, plus a genuine PicoBlade crimper that
  costs more than every connector you will ever use.
- **Pins 8 and 9 are not logic level.** Pin 9 carries +9 V and pin 8 sits at
  4.5 V. Both exceed the input range of the usual 5 V-tolerant 24 MHz logic
  analyzer clones. Route only pins 2, 3, 4 and 6 to the analyzer, and keep 8 and
  9 on separate, clearly marked header positions.

---

## 5. Capture and correlation

| item | ~cost | why |
|---|---|---|
| **Raspberry Pi Pico** | 5 | Two hardware UARTs at 9600 8E1, watching panel TX and panel RX *simultaneously*, each frame timestamped in microseconds and streamed to USB. |
| logic analyzer | owned | Keep it for bit-level questions and anomalies, not for the 101-step sweep in `CANBUS.md` T6. |

The Uno's bit-banged single channel cannot comfortably watch both directions at
once, and the direction that matters here — head unit → panel — is precisely the
one never captured. Two hardware UARTs, timestamps from the same host that sends
the CAN sweep, and the merge in `CANBUS.md` §8 becomes trivial.

Capture rate rule still stands: ≥ 500 kHz, ideally 1 MHz. `README.md` explains
why 20 kHz corrupts data bits 5–7 while still looking plausible.

---

## 6. Probing and inspection — the underrated purchase

`BACKLIGHT.md` §5 already says the DMM tip is several times wider than the gap
at 0.65 mm pitch. That is the actual bottleneck on the last unknown node.

| item | ~cost |
|---|---|
| USB microscope, or a decent loupe | 25–40 |
| fine-tip / needle DMM probes | 10–20 |
| component tester (LCR / transistor tester) for the `N_NBASE` capacitor, T5 | 15–25 |
| ESD strap | 5 |

Roughly 60 EUR, and it is aimed squarely at the question that is blocking.

---

## 7. Sourcing a head unit to sniff

The bricked unit may not be recoverable enough to run `CANBUS.md` T5 onward. A
second, working unit is the fallback — and it does not have to be a good one.

### The state of the bricked unit is unknown — check before you spend

The known behaviour — powers on from the panel button, boots to the PIN screen,
shuts down after about 30 minutes — was all observed **before** the failed
software update. It describes a working unit of this part number. It says
nothing about the one on the bench now.

> **Correction.** An earlier revision of this section read that behaviour as
> current and concluded the donor unit was a fallback rather than a
> prerequisite. That was based on a misreading of when the observations were
> made, and it is withdrawn.

So run `CANBUS.md` T2 first — power it, press the button, watch the current. It
costs nothing beyond the supply you were buying anyway, and it is the difference
between "the donor unit is contingency planning" and "the donor unit is the
project."

### Pin-locked is fine. Prefer it.

Component protection is exactly the fault to look for. A unit with active
component protection **still boots, still lights its display, and still runs its
illumination handling** — it simply refuses to operate as a radio. For this
project that is a complete unit, because everything of interest happens between
power-on and the code prompt.

Sellers describe these as *"no code"*, *"SAFE"*, *"component protection active"*,
*"pulled from a scrapped car, code unknown"*. They sell for a fraction of a
coded unit, and the discount is for a feature you do not want.

### Other faults that are harmless here

| advertised fault | relevance |
|---|---|
| DVD / nav drive dead, will not read discs | **none.** The most common RNS-E failure and the biggest price cut. Irrelevant to the panel link |
| no navigation disc included | none |
| scratched or marked screen | none, and it will not affect resale much either |
| missing trim, bezel or cage | cosmetic; check what you are missing is not the fascia holding the panel board |
| wrong car / wrong fascia colour | see below — possibly a bonus |

### Faults to avoid

- **"No power", "dead", "not turning on"** — that is the unit you already have.
- **Water damage** — corrosion makes every subsequent measurement untrustworthy.
- **"Untested" at a non-scrap price.** Untested is fine at scrap money; it is a
  gamble priced as a certainty otherwise.
- **Wrong generation.** See below.

### Generation matters, car does not

All reverse engineering so far has been on an `8P0 035 192 H` panel. Stay within
the **192** series. The later **193** ("high") units are a different generation
and `README.md` already flags that the protocol is unconfirmed there.

Within the 192 series, part numbers commonly seen include `8P0 035 192` (A3 8P),
`8E0 035 192` (A4 B7) and `8J0 035 192` (TT 8J) — verify any specific number
before buying, these families are not always cleanly separated.

The unit photographed in [`rns-e-pinout.png`](rns-e-pinout.png) is an
`8E0 035 192 Q`, i.e. an A4 B7 part, while `README.md` records the
reverse-engineered panel as `8P0 035 192 H` from an A3 8P. Both are 192 series.
If those two boards end up on the bench together, the cross-variant test below
is not hypothetical — it is already running.

**Buying a 192 from a different car is arguably better than buying another A3
one.** The fascia and button legends differ, but the panel board and its 9-pin
link are what this project cares about, and `README.md` states the cross-variant
assumption explicitly:

> I don't expect this to change for other `192` versions, but I cannot confirm
> the protocol is the same

A second variant tests that assumption for free, as a side effect of work you
were doing anyway. If the boot handshake and frame format hold across two
different 192 units, that sentence in the README can be strengthened from an
expectation to an observation.

### A second unit is also a reference

Beyond the CAN work, a working unit is the only way to answer questions about
the bricked one: what its boot current profile *should* look like, what the
head-unit-to-panel conversation *should* contain, and — depending on how the
firmware is stored — whether there is a route back for the bricked unit at all.
Do not plan on the last one, but do not rule it out before looking.

### K-Line — check this before writing the brick off

The label shows **`B5 K-Line`**, the ISO 9141 diagnostic line. That is a second,
completely independent channel into the bricked unit — the one a dealer tool
uses. Spend 10–20 EUR on a USB KKL cable and find out whether the brick answers
diagnostics.

It is worth doing early precisely *because* the unit's current state is unknown.
A unit that answers on K-Line is running enough firmware to service diagnostics,
may hand over fault codes naming what actually broke, and may in principle be
reflashable. A unit that does not answer has told you something too.

Do not plan on a recovery. Do find out — it is the cheapest question you can ask
of the bricked unit, and together with `CANBUS.md` T2 it decides whether you are
buying a donor unit or not.

### Where to look

Second-hand car-part marketplaces and breakers, in rough order of how often
these turn up cheap: German classifieds (eBay Kleinanzeigen), eBay.de, Polish
and Lithuanian sellers on eBay and Allegro, and local scrapyards. Search the
part number rather than the model name; scrap listings are usually written from
the label.

Expect roughly 40–90 EUR for a pin-locked or dead-drive unit, versus several
hundred for a coded, fully working one. **Buy the cheap one.**

### Keeping it resellable

The plan is: buy, bench-test, open enough to reach the panel connector, sniff,
close, sell. That works, but only with discipline about the "open" step.

1. **Bench-test before opening.** Power it, confirm it boots, confirm the panel
   lights. If it is DOA, return it — an unopened unit is returnable and an
   opened one is not.
2. **Photograph every step.** Each screw removed, each connector unplugged, in
   place, before it moves. This is the difference between a 20-minute reassembly
   and an evening.
3. **Sort the screws by step.** RNS-E assemblies mix lengths and types; a screw
   in the wrong hole cracks a boss or bottoms out on a board.
4. **Open only as far as the 9-pin connector.** The fascia and the front panel
   board are the target. Leave the DVD mechanism, its ribbon, and the optical
   assembly alone entirely — that is the most fragile and most failure-prone
   part of the unit, and disturbing it is how a working unit becomes a dead one.
5. **Do not solder to either board.** The tap in §4 is a pass-through cable and a
   perfboard; it leaves no trace. A resold unit with flux residue and reflowed
   joints is a resold unit with an argument attached.
6. **Plastic pry tools, not screwdrivers**, on the fascia clips. Broken clips are
   visible, permanent, and the first thing a buyer notices.
7. **ESD strap on before the case comes off.**
8. **Note the serial and part number before disassembly.** You will want them for
   the listing, and for correlating any protocol difference you find.

Disclose what you did when you sell it. "Opened to access the front panel
connector, no modifications, reassembled with original hardware, working as
purchased" is an honest listing and costs nothing against the price.

---

## 8. Budget

| tier | contents | ~cost |
|---|---|---|
| **Do-it-now** | probing and inspection kit (§6) — unblocks `BACKLIGHT.md` T2 | ~60 |
| **Minimum CAN** | MCP2515 module, quadlock pigtail, fuse, resistors | ~20 |
| **Recommended CAN rig** | isolated USB-CAN, bench PSU, quadlock pigtail, fuse, PicoBlade cables, Pico | 130–180 |
| **K-Line probe** | USB KKL cable — tests the brick before you replace it | 10–20 |
| **Donor head unit** | pin-locked or dead-drive 192-series | 40–90 |

The recommended rig plus a donor unit lands around 200–290 EUR. The probing kit
at 60 EUR is the best value in the table, because it addresses the node that is
actually blocking. The KKL cable is the best value per euro, because it is the
cheapest question you can ask the bricked unit and its answer decides whether
the donor unit is a fallback or a purchase you have to make.

---

## 9. Not needed

- A navigation DVD. Nothing here requires the unit to navigate.
- A gateway module. Useful for realism, but the point of the bench is to send
  the frames yourself.
- A CAN-FD interface. This bus is classical CAN at 100 kbit/s.
- A second CAN adapter. Man-in-the-middle between a real car and the unit is a
  different project.
- A more expensive logic analyzer. The existing one is adequate at 1 MHz for a
  9600 baud link; §5 moves the routine capture off it anyway.
- A 15 A inline fuse. The unit already has one; see §2.
- Anything to drive an ignition line. There isn't one.

---

## License

This document is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Copyright 2026 André Carvalho — [rnse project](https://github.com/RedRoserade/rns-e).
If you reuse any of it, please credit it and link back.

Product names are used descriptively to identify parts that fit this bench. No
affiliation with, or endorsement by, any manufacturer or vendor is implied.
