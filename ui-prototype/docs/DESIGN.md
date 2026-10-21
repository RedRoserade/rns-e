# Design notes — the RNS-E look and behaviour

What we are imitating, extracted from the operating manual (`../rns-e.pdf`).
Page numbers are the **printed** ones; add roughly 11–14 to get the PDF page
(the PDF has divider pages).

The aim is the original's grammar — same layout, same controls, same
behaviour — rendered at a modern standard: anti-aliased curves, smooth
transitions, crisper type. Not a pixel copy.

---

## 1. Screen anatomy (p. 27-28)

```
 TL label            Title              TR label
 (  ╭──────────────────────────────────────╮  )
 (  │ Subtitle                             │  )
 (  │ ●─ Selected row         ▼ value      │  )
 (  │    Row                  ▷            │  )
═(  │    Row                               │  )═
 (  │  ▼                                   │  )
 (  ╰──────────────────────────────────────╯  )
 BL label                              BR label
```

| Element | Notes | Implemented in |
|---|---|---|
| **Title line** | Main function name, centred, bold, accent colour. "Setup X" when in Setup. | `Frame.qml` |
| **Corner labels** | One per control button around the knob (TL, TR, BL, BR). Grey; the active one is highlighted. | `Frame.qml` |
| **Arcs** | A crescent on each side, thickest at mid-height. Each is split by a grey tab at mid-height into two halves; each half belongs to the nearest corner and lights up in the accent colour while that corner's submenu is open (p. 18; p. 57 fig. 54). | `Frame.qml` (`ArcHalf`) |
| **Panel** | Thin accent outline, straight top/bottom, sides bowing out to follow the arcs. | `Frame.qml` |
| **Subtitle** | Submenu name, top-left inside the panel, accent colour (p. 28 fig. 22). | `Frame.qml` |
| **Display centre** | Lists, station list, map, etc. | `qml/screens/*` |

### List conventions (p. 29)

- **Cursor**: a small ring/dot on the panel's left curve, joined by a short
  line to the selected row. The selected row's text is white; others are in
  the accent colour.
- **▲ / ▼** at the top/bottom of the list: more items that way.
- **▷** after a row: opens a submenu. **▶** (filled): the selected row's submenu.
- **Value boxes**: `▼ value` in a filled accent box right of the row
  (p. 27 fig. 21; p. 169 fig. 180) — selecting opens a choice list.
- **Checkbox**: ✔ in a box (p. 27 fig. 21, "Voice information").

`Frame.panelLeftAt(y)` gives the x of the panel's left curve at height y, for
putting the cursor on it.

## 2. Colour

Accent per function. Setup takes its function's accent.

| Function | Accent | Source |
|---|---|---|
| Radio, CD/MP3 (media) | orange `#ff6a13` | p. 33, 56, 169 — confirmed |
| Navigation | cyan-blue `#27b4ec` | p. 27-32 — confirmed |
| Info | cyan-blue | assumed (shares the manual's NAV/INFO chapter colour) |
| Name, Tel | ? | unverified — placeholder blue |
| Car | red? | assumed (CAR/SETUP chapter colour); unverified |
| PIN entry | red | p. 14 fig. 6 |

Background is black. Arcs at rest are a dark shade of the accent; lit, the
full accent. The panel has a faint accent glow at the top (our addition).

## 3. Controls and behaviour (p. 15-20)

| Control | Behaviour |
|---|---|
| **Function buttons** (FM/AM, CD/SD, NAME, TEL, NAV, INFO, CAR, SETUP) | Open that function, at the screen you were last on in it — **history** (p. 20). If already in that function: go to its main menu — **home** (p. 20). |
| **SETUP** | Opens the Setup main menu *for the current function* ("Setup Radio"). Press again to leave (p. 16). Setup submenus Settings / Sound / Display are the same in every function (p. 169). Setup is not kept in history (p. 20). |
| **Control buttons** (4, around the knob) | Open the submenu shown in that screen corner; corner + arc half light up (p. 17-18). |
| **Control knob** | Rotate: move the cursor. Press: confirm (p. 17). Keep rotating past the end to reach more items. |
| **RETURN** | Up one level within the function; cancels an unconfirmed selection (p. 18). |
| **|<< >>|** | Radio: previous/next station in the list. CD/MP3: previous/next track; hold to seek (p. 18-19). |
| **Volume knob** | Volume. Push = on/off (p. 19). Not on the panel's serial bus — see `../../docs/PROTOCOL.md`. |

## 4. Screens catalogue (for later)

| Screen | Page | Notes |
|---|---|---|
| Radio main (station list) | 56-58 | "Radio FM"; corners Memory / Band / Tuning / Sound |
| Radio band | 57 | FM / AM list |
| Setup Radio | 169 | Station reception (▼ local), Station display (▼ on), Delete stored stations ▷ |
| Setup Navigation | 27 fig. 21 | Map scheme, Orientation, Map type (value boxes), Map contents ▷, Voice information ✔ |
| Navigation main | 27 fig. 20 | Region / City / Street entry fields, Special destination ▷ |
| Speller | 30-32 | Ring of characters around a central bubble; knob rotates the ring. Signature RNS-E element. |
| Control wheel | 33 | Segmented ring for media transport (« » × NAME …) around elapsed time |
| PIN entry | 14 | Speller variant, red |

## 5. Our additions ("more modern")

Ideas, not decisions:
- Short eased transitions between screens and on cursor moves (Theme.animMs).
- Subtle glow on lit arcs and the selected row.
- Anti-aliased everything; an open font close to the original (see PLAN.md).
- Proper scrolling lists instead of page jumps.

## 6. Side bows as a real circle (derivation)

Goal: the left and right "bows" of the frame are arcs of one circle, with a
rectangular safe area inscribed in it. Screen 800x480; origin at the screen
centre O for the maths, QML centre is (400, 240).

Inputs (the only hardcoded values, belong in `Theme.qml`):

- side margin 20 px, top/bottom margin 40 px (assumes symmetric margins, so
  the circle is centred on the screen)

Derived:

| Quantity | Formula | Value |
|---|---|---|
| radius R | (800 - 2*20) / 2 | 380 px |
| half-height h | (480 - 2*40) / 2 | 200 px |
| alpha | asin(h / R) | ~31.76 deg |
| half-width w | R*cos(alpha) = sqrt(R^2 - h^2) | ~323.1 px |
| safe area | 2w x 2h | ~646.2 x 400 px |
| bulge | R - w | ~56.9 px |

Right triangle: hypotenuse = radius O->B, B = (w, h) is a safe-area corner on
the circle, A = (w, 0) is the right angle, alpha sits at O measured from the
horizontal. So sin(alpha) = h/R and cos(alpha) = w/R (unitless ratios; the
pixel values come from multiplying by R). Pythagoras gives w directly without
alpha; alpha is only needed for the arc angles.

QML arcs (`PathAngleArc`: degrees, y points down, positive sweep = clockwise,
0 deg = +x):

- right bow: startAngle = -alpha, sweepAngle = 2*alpha
- left bow: startAngle = 180 - alpha, sweepAngle = 2*alpha
  (180 + alpha would start at the upper-left end, and a clockwise sweep from
  there runs away from the bow)

Convert `Math.asin` radians to degrees once, in a readonly property.

Open: is R the centreline, outer or inner edge of the bow's stroke? Shifts
the numbers by half the stroke width. And whether content fills the whole
safe area or gets extra inner padding.
