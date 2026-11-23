# Design language: the modernised RNS-E

The rules behind the mock-ups and storyboards. Use them to build the QML
screens and to draw new storyboards. `DESIGN.md` says *what* the RNS-E does,
taken from the manual. This file says *how it looks and moves* in our version.

- Storyboards and mock-ups: <https://claude.ai/artifact/TmXG6gnNZjaPNCLRagaSCy>
  (page **Radio storyboard** and **Home storyboard** are canonical; page
  **Explorations** holds earlier ideas, including the rejected Metro row).
- All values are **real pixels on the 800×480 screen** (decision 4 in
  `PLAN.md`). No scaling inside the layout.
- When a storyboard and this file disagree, fix one of them; don't let the
  code pick a third answer.

---

## 1. Principles

1. **Keep the RNS-E's rules, update the finish.** Black ground, one accent per
   function, a centred title, four corner labels bound to the four buttons
   around the knob, the bowed side arcs, the cursor on the left arc, RETURN = up
   one level.
2. **Every on-screen action has a panel equivalent.** The knob, the four corner
   buttons and RETURN must reach everything. Touch is a shortcut, never the
   only way.
3. **Accent means state.** Use the accent for what is selected, open, playing
   or lit. Resting text is white or grey, not accent.
4. **Content stays put.** Turning the knob moves the cursor, not the layout.
   Context (now playing, details) lives in a fixed right-hand column.
5. **Small choices float, big content takes over.** A corner with a handful of
   options opens a *sheet* over the current screen; a corner with a long list
   or a task takes the whole panel.
6. **Content-first screens drop the chrome.** When the content *is* the screen
   (the map), drop the title and arcs and float the four corner pills over it.
7. **Quiet.** No gradients, textures, bevels or emoji. Glow is reserved for
   things that are lit (§6).

---

## 2. Screen geometry

```
 y=0   ┌──────────────────────────────────────────────────────┐
       │[◜ Memory]          Radio FM               [Band ◝]   │  top bar, 48 px
 y=48  │ (                                                  ) │
       │(  STATION LIST                                      )│
       │(  ●─[ Selected row          98.0 ]   now playing     )│  content
       │(     Row                    95.7     column          )│  y 48…432
       │ (                                                  ) │
 y=432 │[◟ Tuning]       ── band scale ──          [Sound ◞]  │  bottom bar, 48 px
 y=480 └──────────────────────────────────────────────────────┘
```

| Thing | Value |
|---|---|
| Screen | 800×480, background `#000000` |
| Top / bottom bar | 48 px each (y 0–48, 432–480). Title and corner chips live here. *Changes `Theme.barHeight` from 40 to 48.* |
| Arc circle | centre (400, 240), radius R = 380 |
| Arc ends | y = 48 and y = 432, i.e. x = 72.1 (left) and 727.9 (right) |
| Arc midpoint gap | y 228–252 (24 px), splits each arc into two halves |
| Arc on the left at height y | `x = 400 − √(380² − (y − 240)²)` |
| List column | x 56–448 (392 wide) |
| Detail column | x 484–720 (≈236 wide) |
| Eyebrow label | x 72, y 54 |
| Sheet area | inside the arcs: x 76–724, y 52–428 |

The left arc at y = 240 sits at x = 20, and at the bar edges at x = 72. Anything
placed near the sides must stay right of the left arc (and left of the right
one) at its own height. Use the formula, not a fixed margin.

---

## 3. Colour

### 3.1 Neutrals

| Token | Hex | Use |
|---|---|---|
| `bg` | `#000000` | screen |
| `surface1` | `#0e0e0e` | sheets, Home cards |
| `surface2` | `#141414` | corner chips |
| `surface3` | `#1a1a1a` / `#1c1c1c` | tool buttons, logo tiles, card buttons |
| `border1` | `#1f1f1f` | Home card border |
| `border2` | `#262626` | chip border |
| `border3` | `#2e2e2e` | sheet border |
| `border4` | `#333333` / `#3a3a3a` | logo tile, badge outline, scale ticks |
| `text` | `#ffffff` | selected rows, headings, big numbers |
| `text2` | `#d4d4d4` | chip labels, icons, secondary values |
| `text3` | `#a8a8a8` | resting list rows |
| `text4` | `#8a8a8a` | eyebrows, hints, units, trailing values. **Lowest grey allowed for text** (5.9:1 on black) |
| `disabled` | text at 50–55 % opacity | last visible row, unavailable items |

### 3.2 Function accents

Each function has one accent and four derived shades. Derive them once in
`Theme.qml`; don't compute them ad hoc in screens.

| Function | `accent` | `accentLight` (accent text on black) | `accentDeep` (fills) | `accentArc` (arcs at rest) | `onAccent` (text on accent) |
|---|---|---|---|---|---|
| Radio, Media | `#ff6a13` | `#ff8a45` | `#2a1406` | `#3a1a08` | `#1a0800` |
| Nav, Info | `#27b4ec` | `#8fd6f3` | `#0f2a36` | `#0d3a4c` | `#00151f` |
| Name, Tel | `#66ff01` | `#b8ff8f` | `#132a05` | `#1d4200` | `#0b1a00` |
| Car (unverified) | `#fc0417` | — | — | — | — |
| Home / neutral | `#e6e6e6` | `#ffffff` | `#1c1c1c` | `#262626` | `#111111` |

- **Row highlight**: `accent` at 14 % alpha (12 % for the green).
- **Value chip at rest**: `accentDeep` fill, pale accent text (`#bfe9fa` cyan,
  `#ffc9a6` orange).
- **Text on an accent fill always uses `onAccent`**, never white. White on the
  orange, cyan and green fails contrast.
- **Lists use the cursor and row highlight, not colour alone**, so the
  selection still reads for colour-blind users and in sunlight.

### 3.3 Map palette (native navigation)

`#0d1418` ground, `#1e2a31` major roads (12 px), `#172128` minor roads (6 px),
`#0a1d29` water, `#111c21` blocks, route = Nav `accent` 9 px, own position =
white arrow with an 18 px `accent` halo at 18 % alpha. Street labels Barlow 13
`#6b7f8a`.

---

## 4. Typography

**Families:** **Barlow** (400/500/600/700) for text, and **Barlow Semi
Condensed** (400/500/600) for numbers (frequencies, times, distances, values).
Both are SIL OFL; bundle them in `qml/fonts/`. Turn on tabular figures
(`font.features: { "tnum": 1 }`) for anything that changes while you watch.

> **Decided (decision 9 in `PLAN.md`):** Barlow is the default and the only
> font the project ships. **Audi Sans is optional and supplied by the user**:
> it's proprietary, so neither the repo nor any built image may contain it.
> If the files are present locally, `Theme.qml` uses them instead of Barlow.
> Every size in this document is tuned for Barlow. Audi Sans runs slightly
> wider, so with it loaded, check that row labels and chip labels still fit.
> Keep the numeric roles on Barlow Semi Condensed either way.

| Role | Family | Weight | Size | Colour | Example |
|---|---|---|---|---|---|
| Title | Barlow | 600 | 22 | accent | "Radio FM" |
| Home title (clock) | Barlow SC | 600 | 26 | text | "14:32" |
| Corner chip label | Barlow | 500 | 18 | text2 | "Memory" |
| Eyebrow | Barlow | 600 | 12, tracking .14 em, UPPERCASE | text4 or accent | "STATION LIST" |
| List row | Barlow | 400 | 22 | text3 | "Antena 1" |
| List row, selected | Barlow | 600 | 24 | text | "Hertz 98 FM" |
| Trailing value | Barlow SC | 500 | 18 | text4 / accentLight when selected | "98.0" |
| Detail heading | Barlow | 600 | 28–30 | text | station or contact name |
| Big number, hero | Barlow SC | 600 | 40–54 | text or accent | "98.0", "2:41" |
| Big number, card | Barlow SC | 600 | 30–46 | text or accent | "300 m" |
| Unit next to a number | Barlow | 500 | 14–18 | accent or text4 | "MHz" |
| Sheet row | Barlow | 400 (600 when selected) | 19–24 | text3 / text | "Bass" |
| Sheet sub-line | Barlow SC | 500 | 14 | text4 / accentLight | "87.5 – 108 MHz" |
| Button label | Barlow | 600 | 19–20 | onAccent | "Store Hertz 98 FM" |
| Hint line | Barlow | 500 | 13–14 | text4 | "Turn to move · press to change" |
| Badge | Barlow | 600 | 12, tracking .08 em | `#cfcfcf` | "RDS" |

Writing rules:
- Sentence case everywhere ("Voice information"). UPPERCASE only for eyebrows
  and badges.
- Titles are "Function Band/Mode": "Radio FM", "Setup Navigation".
- Separate facts on one line with " · ".
- A hint line says what the knob does on this screen: turn, press, RETURN.

---

## 5. Components

Sizes are in px. "r" is the corner radius.

### Corner chip (one per corner button)
- 40 tall, padding 0 14, r 12, gap 8; `surface2` fill, 1 px `border2`.
- Inset 10 from the side edge and 6 from the top or bottom edge.
- **Corner glyph**: a 12×12 quarter-arc, 2 px stroke in `accent`, on the
  outer side of the label. It bulges toward its corner:
  TL `M2 10 A8 8 0 0 1 10 2`, TR `M2 2 A8 8 0 0 1 10 10`,
  BL `M2 2 A8 8 0 0 0 10 10`, BR `M10 2 A8 8 0 0 1 2 10`.
- **States**:
  - rest
  - **open**: `accent` fill and border, `onAccent` label and glyph
  - **dimmed**: 50 % opacity while another corner is open
  - **floating** (over a map): `rgba(10,10,10,.84)` fill, 1 px
    `rgba(255,255,255,.1)` border, 8 px backdrop blur, shadow
    `0 2 10 rgba(0,0,0,.5)`
- A corner with no function shows no chip. Don't draw an empty one.
- Touch: the hit area is the chip plus its corner of the bar, so the target is
  bigger than 44×44 even though the chip is 40 tall.

### Arcs
- 5 px stroke, round caps, two halves per side.
- Rest: `accentArc`. **Lit** (its corner is open): `accent` plus glow (§6).
- One half is lit per open corner; nothing is lit on a function's main screen.
- The right arc may show a scroll position as a 2 px `accentLight` segment.
- Hidden on full-bleed screens (the map).

### Cursor
- A ring of r 7 with a 3 px `accent` stroke and black fill, centred on the left
  arc at the selected row's centre height (use the formula in §2).
- A 2 px `accent` line runs from the ring's edge to the row's left edge
  (x 56).
- In Setup the ring is white and the line stays `accent`.
- In a sheet, the ring sits on the sheet's left edge instead of the arc.

### List row
- 52 tall on a 56 pitch, r 10, padding 0 16, x 56–448 (full width up to 724
  for Setup lists).
- Selected: `accent` 14 % fill, label 600/24 white, trailing value in
  `accentLight`.
- More items below: the last row at 55 % opacity, plus a "▾ N more" hint
  (13 px, text4).
- Six visible rows is the norm.
- Trailing items:
  - value (Barlow SC 18)
  - value chip
  - switch
  - chevron (22 px, 2.5 px stroke, text4) = opens a submenu
  - check (2.5 px stroke, accent) = current choice

### Value chip (replaces the RNS-E "▼ value" box)
36 tall, padding 0 12, r 9. At rest: `accentDeep` fill and pale accent text.
On the selected row: `accent` fill and `onAccent` text. Label 500/17, then "▾".

### Switch
52×30, r 15. On: `accent` track with a white 24 px thumb on the right. Off:
`#333` track with the thumb on the left.

### Slider (sheet rows)
- Track: 4 px tall, r 2, `#333`. On the selected row it turns `accentDeep`.
- Thumb: 20 px circle, `text2`. On the selected row it turns `accent` with a
  4 px halo of `accent` at 30 %.
- Centre tick (zero): 1×14 `#555`.
- Value: Barlow SC 16, right-aligned, 28 wide.

### Buttons
- **Primary**: 52 tall, r 14, `accent` fill, `onAccent` label 600/19–20. At
  most one per screen.
- **Tool**: 44 tall, r 10–12, `surface3` fill, icon in text2.
- **Seek, text and icon**: 44 tall, padding 0 16, r 12.

### Sheet (a corner's overlay)
- Anchored to its corner, inside the sheet area (§2).
- r 18 everywhere except the origin corner, which is r 6. That smaller corner
  is how you tell where the sheet came from.
- `surface1` fill, 1 px `border3`.
- Shadow 40 px blur, `rgba(0,0,0,.8)`, offset 20 px away from its corner.
- An eyebrow names the sheet (in `accent`).
- Rows are 48–64 tall, with the cursor on the sheet's left edge.
- Behind it, the main screen drops to **28 % opacity**. The title, the chips
  and the lit arc stay at full strength.
- Sizes used: Band 276×266 (TR), Tuning 648×232 (BL, full width), Sound
  308×328 (BR).

### Home card
- **Full**: 200×340. **Half**: 200×166. Two halves stack with an 8 gap.
- Three columns at x 84, 300 and 516; top y 66.
- r 16, `surface1` fill, 1 px `border1` border, padding 16, gap 8.
- Each card starts with an eyebrow in its function's accent ("RADIO FM").
- Then one hero value: a big number or name. Then at most two supporting
  lines. Optionally a button row at the bottom.
- Focused: 2 px white outline, offset 3. Knob order is column by column, top
  to bottom.

### Home edit mode (SETUP on Home)
- **Title**: "Edit Home", in the neutral accent.
- **Content**: the cards drop to 45 % opacity.
- **Column slot**: a 2 px dashed `#555` outline around the whole column,
  212×352 at r 20 (6 px outside the cards). Focused: dashed white.
- **Size tag**: centred on the slot's bottom edge, half over it. 26 tall, r 13,
  `surface3` fill, 1 px `#3a3a3a` border, label 600/12 uppercase ("FULL ·
  RADIO", "HALF + HALF"). Focused: `#e6e6e6` fill with `#111` text.
- **Corner chips** get a 1.5 px dashed `#6a6a6a` border instead of the solid
  one.
- **Pickers** are sheets, but the content behind them goes under a black
  scrim at 55 % rather than to 28 % opacity. The edited element (slot or
  chip) stays above the scrim.
  - The card picker opens next to its column.
  - The corner picker opens from its corner, and that chip shows as open.
- **Picker row**: 38 tall on a 40 pitch, r 10, with a 9 px dot in the item's
  accent, label 400/19 (600 white when focused), and a check on the current
  item.
- **Segmented control** (Full | Half, Since start | Long-term): a `surface3`
  track with r 9–12 and 2–3 padding. The selected segment is the accent with
  `onAccent` text 600; the rest are text3 500.

### Floating card (on the map)
`rgba(0,0,0,.86)` fill, 1 px `#1f2a30` border, r 14 for cards and r 10–12 for
pills.

### Small parts
- **Logo tile**: 92², r 18, `surface3` fill, 1 px `#333` border; it shows
  initials when there's no logo.
- **Avatar**: a circle of the same size, in `accentDeep` with accent initials.
- **Badge**: padding 3 7, r 6, 1 px `#3a3a3a` border.
- **Signal**: 4 bars, 4 wide on a 7 pitch; heights 6, 10, 14 and 18. Unlit bars
  are `#4a4a4a`.

---

## 6. Depth: shadows and glow

There are only two kinds of depth:

1. **Shadow** lifts a sheet or floating element off what's behind it. Use a
   large soft black shadow (40 px blur, 0.8 alpha) for sheets and a small one
   (10 px, 0.5) for pills over a map. Never use shadow on things that sit in
   the layout.
2. **Glow** means *lit*: `drop-shadow 0 0 6–8 px accent @ 60–70 %`. Only these
   get it:
   - a lit arc half
   - the selected segment of the control wheel
   - the tuning needle
   - the selected speller letter

   At most one glowing thing per screen besides the arc.

In QML: `MultiEffect { shadowEnabled: true; shadowBlur; shadowColor }` for
both. Glow is a coloured shadow with zero offset. Watch the cost on the Pi;
cache it with `layer.enabled` on static items.

---

## 7. Radii and spacing

| r | Used for |
|---|---|
| 6 | badge, a sheet's origin corner |
| 9 | value chip |
| 10 | list row, tool button, map pill |
| 12 | corner chip, seek button |
| 14 | primary button, floating map card |
| 16 | Home card |
| 18 | sheet, logo tile |
| full | switch, cursor ring, avatar, slider thumb |

Spacing comes in steps of 4. The common gaps are 8 (inside chips, between
half cards), 12 (detail column stack), 16 (card and row padding) and 24 (sheet
padding).

---

## 8. Motion

All motion is ease-out cubic going in and ease-in cubic going out (Qt:
`Easing.OutCubic` / `Easing.InCubic`). No springs, no overshoot, no bounce.
Closing is faster than opening.

| What | How | Duration |
|---|---|---|
| Cursor moves to the next row | the ring slides *along the arc* (animate y, derive x from §2); the highlight slides with it | 120 ms |
| List scrolls past the edge | rows glide by one pitch | 160 ms (`Theme.animMs`) |
| Corner opens a sheet | sheet fades in and slides 24 px from its corner; the arc half and chip light up in step; the background dims to 28 % | 180 ms in / 140 ms out |
| Switch from one corner's sheet to another | the old one leaves (140) while the new one enters (180), overlapping | ≈180 ms |
| Corner opens a full-panel screen | cross-fade; the new list slides in 24 px from the left | 220 ms in / 140 ms out |
| RETURN to the level above | reverse of whatever opened it | as above |
| Function button (switch function) | cross-fade the content; title and accent colour blend | 200 ms |
| Focus moves between Home cards | outline fades out on the old card and in on the new | 100 ms |
| Live value changes (RDS text, next turn) | cross-fade the text | 300 ms |
| Numbers that tick (time, frequency) | no animation, just update | — |
| Enter or leave Home edit mode | cards gain or lose the dashed edit outline; size tags fade | 200 ms |
| Map | pan and zoom follow the car smoothly; pills never animate | — |

The sheet's auto-close is 8 s of no input. If the frame rate drops on the
Pi, drop the blur before you drop the motion.

---

## 9. Iconography

- Inline stroke icons on a 24 grid: 1.6–2.5 px stroke, round caps and joins,
  in text2. Transport controls (play, pause, previous, next, seek) are
  **filled**.
- Sizes: 12 (corner glyph), 16–18 (inside buttons), 20–24 (tool buttons),
  40–72 (hero turn arrows on nav cards).
- If you need an icon set, use Lucide or Tabler (both MIT, same stroke style),
  drawn as SVG through `Shape`/`Image`. No emoji, no icon fonts with brand
  glyphs.
- Turn arrows are a thick (9/72) white stroke with a solid triangle head.

---

## 10. Interaction model (panel ↔ screen)

| Input | Effect |
|---|---|
| Corner button | open that corner's sheet or screen. The same button again closes it; another corner switches to its own |
| Knob turn | move the cursor or focus. Inside a value (slider, tuning) it changes the value |
| Knob press | confirm: tune, open, toggle, or enter value-edit on a slider row |
| Knob hold | secondary action on the item (e.g. Memory slot: Replace / Move / Delete) |
| RETURN | up one level: close a sheet, leave a submenu. At a function's top level → Home (pending in `navigation.py`) |
| RETURN hold | Home from anywhere (proposed) |
| SETUP | Setup for the current function. **On Home: edit mode** |
| Function button | history, then that function's main screen (unchanged from RNS-E) |
| `|<< >>|` | previous/next item in the current source, wherever the cursor is |
| Touch | tap = move the cursor there and press; drag scrolls lists; tap outside a sheet closes it; tap the title = Home (proposed) |

---

## 11. Screen templates

1. **List + detail**: list on the left with the arc cursor, a fixed detail
   column on the right. Used by Radio, Memory and Telephone.
2. **Sheet over main**: the main screen dimmed, with a corner sheet on top.
   Used by Band, Tuning and Sound.
3. **Instrument**: one central figure with the context around it. Used by the
   media control wheel and the speller ring.
4. **Full bleed**: no title, no arcs, floating pills. Used by the map and
   projection.
5. **Cards**: Home.

A new screen should be one of these. If it doesn't fit any of them, add a
template here first.

---

## 12. Storyboard conventions (for continuing them)

- One canvas page per function: the main screen in the centre of a 3×3 grid,
  and each corner's screen in the diagonal cell matching its corner. The edge
  cells hold notes: corner rules (top), input (left), content (right) and
  motion (bottom).
- Extra flows (edit mode, pickers) go in a row below the grid, left to right in
  the order they happen.
- Use realistic sample data (Portuguese stations, Lisbon streets), never lorem
  ipsum. Mark guessed corner labels as guesses in the note.
