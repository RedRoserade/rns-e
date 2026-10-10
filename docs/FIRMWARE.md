# RNS-E firmware update disc — what is on it

Static inspection of an RNS-E firmware update image, done to find where the
head unit decides the front-panel backlight level and why a bench unit's
application never starts (`CANBUS.md` §4–§6).

Companion to `PROTOCOL.md` (the panel serial link), `BACKLIGHT.md` (the LED
driver chain) and `CANBUS.md` (driving the head unit over CAN).

**Status. The layout, the module header, the checksum and the load addresses
are established (§3.3). Three code paths have been traced by disassembly:
CAN `0x635` → KL58s check → the front-panel frame `ADDR 0x06` (§5.2.1); the
panel link's ACK/NAK, init sequence and full address set (§5.5); and the
softkey indicator lamps, screen → `ADDR 0x07` (§5.6).** Everything
else comes from reading the files: headers, directory tables, checksums,
`strings` and literal-pool pointers. Where a claim goes past what the bytes or
the disassembly say, it is marked as an inference. Nothing here has been tested
on hardware.

The firmware itself is not redistributed here.

---

## 1. The disc

Volume label `EU_FW_0313_0743`. `VERSION.TXT`:

```
COMMENT=High;
DISC=8P0060884DJ;
MAP=DJ_EU1;
```

```
00.VNS          update manifest (Aisin AW, built Mar 15 2012)
INDEX.TXT       SOFIDX:0743  NAVVER:V2200815  AUDVER:A2210141
574INDEX.TXT    SOFIDX:0313  NAVVER:V574109D  AUDVER:A5740022  TXTVER:0580
B48INDEX.TXT    SOFIDX:0793  NAVVER:VB48105D  AUDVER:A5740022  TXTVER:0580
LDM.BIN         loader for V220
574/LDM.BIN     loader for V574
B48/LDM.BIN     loader for VB48
LOADING.KWI     74 MB container: all three program sets (§3)
A2210141.MOT    system-MCU firmware for V220 (§4)
A5740022.MOT    system-MCU firmware for V574 and VB48 (§4)
```

**Established:** the disc carries firmware for **three hardware generations**,
selected by the `*INDEX.TXT` the unit matches. The two numbers in the volume
label are two of the three `SOFIDX` values.

| hardware | SOFIDX | nav/UI software | system MCU | build dates |
|---|---|---|---|---|
| V220 | 0743 | V2200815 | A2210141 | 2005–2007 |
| V574 | 0313 | V574109D | A5740022 | Mar 2012 |
| VB48 | 0793 | VB48105D | A5740022 | Aug 2011 |

V574 and VB48 have the same module set and near-identical module sizes, and
share one system-MCU image. Which part numbers map to which hardware version
is **not** recorded on the disc. Inference: V220 is the original 2004-era
unit, and V574/VB48 are later revisions. Which one the bench unit
(`8P0 035 192 H`) is remains unchecked. The software version screen in the
green menu should show it.

## 2. `00.VNS` — the manifest

A fixed-record table. The header gives `VNS`, `1000`, the date, and
`AISIN AW co.,LTD`. After it come 64-byte records of the form `<tag>\0<filename>`
plus a version string:

```
IDX   00.VNS
MAP   01.VNS
ZMAP  02.VNS     V22000 0815
LDR   LDM.BIN    V220     PRG 04.VNS
LDR   /574/LDM.BIN   V57400 109D   V574   PRG 06.VNS
LDR   /B48/LDM.BIN   VB4800 105D   VB48   PRG 08.VNS
```

`0x.VNS` are logical names, not files on the disc. **Inference:** they resolve
to the program sets inside `LOADING.KWI` (§3). Strings inside the modules also
name `KWIFMT.KWI` and `ALLDATA.KWI`, which are not on this disc, so they
presumably live on the map DVD. KIWI is the Japanese car-navigation map format.

## 3. `LOADING.KWI` — the program container

### 3.1 Directory

**Established.** The file is laid out in 2048-byte sectors. At 0x18, 0x58 and
0x98 there is one header per hardware version: the tag (`V220`, `V574`, `VB48`)
and its version string (`0815`, `109D`, `105D`). Each version then has a module
table of 16-byte entries:

```
+0  char[4]  module name
+4  u32      0
+8  u32 BE   offset from the start of the group, in 2-byte units
+12 u32 BE   size in bytes
```

The module tables start at 0x11C (V220), 0x21C (V574) and 0x31C (VB48). The
start offset of each group was found from its `.LDR` magic. The table also
appears to hold each group's start sector: `0x21F4` → 0x10FA000 and `0x57DC` →
0x2BEE000. That reading is likely but not fully decoded.

| group | base in KWI | first module |
|---|---|---|
| V220 | 0x0000800 | byte-identical to `LDM.BIN` |
| V574 | 0x10FA000 | matches `574/LDM.BIN` (first 512 bytes compared) |
| VB48 | 0x2BEE000 | matches `B48/LDM.BIN` (first 512 bytes compared) |

Extraction in a few lines of Python: for each entry, `blob = kwi[base + off*2 :
base + off*2 + size]`.

### 3.2 Modules

Each module starts with a 0x70-byte text header: a type tag (`.LDR`, `.APL`,
`.OS `, `.FNT`, `.ETC`), the version, the build date and time, and
`AISIN AW co.LTD`. All lines end in CRLF and the header ends in `0x1A`. At 0x70
is a 16-byte binary header (§3.3).

| module | type | V220 size | V574 size | contents (from strings) |
|---|---|---|---|---|
| LDM  | .LDR | 0.6 MB | 2.9 MB | loader / updater |
| APFM | .APL | 20 KB  | 22 KB  | small, purpose unknown |
| APM  | .APL | 8.4 MB | 11.6 MB | main application: nav UI, menus, every language's strings |
| AUM  | .APL | 2.9 MB | 7.3 MB | audio, media, Bluetooth phone, MP3/SD |
| DIG  | .ETC | —      | 30 KB  | V574/VB48 only, unknown |
| FONT | .FNT | 1.7 MB | 1.2 MB | fonts |
| OSM  | .OS  | 2.2 MB | 2.8 MB | OS, drivers, CAN, front panel (§5) |
| VRM  | .ETC | 1.3 MB | 1.3 MB | voice recognition |

**Established:** nothing is compressed or encrypted. Every module except FONT
and APFM contains thousands of readable strings.

### 3.3 Module binary header, checksum and load address

**Established for all 23 modules** (V220, V574 and VB48):

```
+0x70  u32 BE  load address
+0x74  u32 BE  length in bytes, counted from 0x70
+0x78  u32 BE  checksum
+0x7C  u32     0
```

- **Checksum:** the 32-bit sum, modulo 2³², of the big-endian words from 0x80
  up to 0x70 + length. It matches every module. Two modules (V220 `FONT`,
  VB48 `OSM`) declare a length that runs 0x70 and 0x48 bytes past the end of
  their `LOADING.KWI` slot. Their checksums still match on the bytes that are
  there, so the missing tail sums to zero and is presumably zero padding.
- **Mapping:** **file offset 0 is the load address.** The text header is loaded
  along with the code, so code at file offset `o` lives at `load + o`.
  Evidence: SH `mov.l @(disp,PC),Rn` literals were collected from each module.
  At this base they land on thousands of function prologues and string starts
  (V574 `OSM`: 7462 prologues and 3665 strings). The best wrong base gets 3024
  and 254. APM, AUM, LDM and V220 OSM give the same result.
- **Segments:** some load addresses are stored without the SH P1 bit while the
  code's own pointers use it. V574 `OSM` says `0x00400200` and runs at
  **`0x80400200`**. Mask with `0x1FFFFFFF` when comparing.

| module | V220 load | V574/VB48 load |
|---|---|---|
| LDM  | 0x8DF00000 | 0x09B60000 |
| APFM | 0x80DFB000 | 0x80B00000 |
| APM  | 0x00280000 | 0x01C00000 |
| AUM  | 0x00AE0000 (code uses 0x80…) | 0x02800000 (code uses 0x828…) |
| DIG  | —          | 0x00E00000 (code uses 0x80E…) |
| FONT | 0x01180000 | 0x00E49000 |
| OSM  | 0x0000C100 (code uses 0x80…) | 0x00400200 (code uses 0x80…) |
| VRM  | 0x81000000 | 0x80C00000 |

The four words at 0x80 are pointers into the module. In AUM, VRM and LDM they
point at pointer tables. Their meaning has not been worked out.

**Confirmed by references.** With this mapping, each of the §5 strings in V574
`OSM` has exactly one literal-pool entry and one instruction that loads it:

| string | address | loaded at |
|---|---|---|
| `fp_dim_can_error` | 0x8047FADC | 0x80604346 |
| `-----KL58S ERROR` | 0x8047FAF0 | 0x806046DC |
| `[FP] fp_set_dimmer ERROR` | 0x8047FB04 | 0x806051DE |
| `[FP] BRIGHTNESS SET [ %d ]` | 0x8047FB78 | 0x8060596C |
| `PWM CAN_Pass_mzas mZas[%02x]` | 0x80480168 | 0x806088C0 |
| `Now skon[%d] Now Kl15[%d]` | 0x804801F4 | 0x80609012 |
| `[FPDRV]   fpdrv hard reset` | 0x804514C0 | 0x80555C94 |

The dimming and power-manager code sits together around 0x80604000–0x8060A000.
The panel driver is separate, near 0x80555C00.

## 4. The two processors

### 4.1 Nav/UI CPU — SuperH, big-endian (`LOADING.KWI`)

- **Established:** the code is dense with SH register pushes (`2f e6 2f d6 2f c6`
  = `mov.l r14/r13/r12,@-r15`) and SH `rts` (`00 0b`).
- The V220 loader's load address is 0x8DF00000, which is in the SH P1
  (cached, untranslated) region. The V574 loader's is 0x09B60000.
- **Inference:** SH-4 class, going by the era and the Renesas middleware. The
  exact part is unknown.
- Bundled third-party code, from copyright strings: Renesas DSP audio
  middleware (2008–2009), Hitachi ULSI Systems libraries, ACCESS Co. FAT
  filesystem (AFFM 1.2.55a), libpng 1.0.3, zlib 1.1.3 and libjpeg.
- V574 `OSM` contains `HDD ATA disk driver for V192`.

### 4.2 System MCU — NEC V850E (`A*.MOT`)

- **Established:** both `.MOT` files are valid Motorola S3 records (every
  checksum verified). Each has the header `AudiRnse`, a start address of 0x3800,
  and code covering 0x3800 to roughly 0x381CA (about 210 KB).
- **Established:** the words at 0x3800, 0x3810, 0x3820, 0x3840, 0x3850 and 0x3860
  decode as V850 `JR disp22` (`80 07 …`, `82 07 …`). They sit on the V850
  16-byte interrupt-vector stride: reset, NMI, …, TRAP0, TRAP1, ILGOP.
- **Inference:** 0x0000–0x37FF is an on-chip bootloader that this update does
  not rewrite. The image size suggests a part with at least 256 KB of flash.
- Contents, from strings: tuner and RDS (`RDS-SCAN`, `TP-INFO`, `AUTOSTOR`,
  `PTY`), the CD changer, anti-theft (`SAFE`, `CODE`, `THEFT PR`), `DIAG`, and
  a table of 8-character status texts (`LOUD ON`, `NO CDC`, `TOO HOT`).
  **Inference:** these are the texts for the cluster display.
- **Searched for and not found:** a table of Audi CAN identifiers. Known IDs
  (`0x271`, `0x2C3`, `0x351`, `0x461`, `0x5C3`, `0x635`, `0x661`, …) were looked
  for as 16-bit values, both raw and shifted by 2 and by 5, and as V850
  `movea`/`addi`/`ori` immediates. No dense cluster came up. Either the IDs are
  built some other way, or CAN is not owned by this MCU at all. §5 suggests the
  second.

## 5. Front panel, dimming and CAN

The useful strings are in the SH **`OSM`** module, not in the V850. Offsets are
decimal positions in the extracted V574 `OSM.bin`.

### 5.1 Front-panel driver

```
FPDRV_TSK                         a front-panel driver task
[FPDRV]   fpdrv hard reset
FPDRV_TMO = %x
fpdrv_DATA
acon_fp_open1 / 2 / 3
-------------broken fpsram
[FP] GET ERROR / [FP] clr ERR
```

**Inference:** this is the head-unit end of the 9-pin link in `PROTOCOL.md`.
The `hard reset` string suggests the head unit can reset the panel MCU, which
would fit the reset behaviour already seen there. The same OSM also has
`Mfl Open Error!!` / `MFL Open Error!!`. MFL is the multifunction steering
wheel.

### 5.2 Dimming — terminal 58s over CAN

One block of strings, in this order (offsets 522459–522616):

```
fp_dim_can_error
-----KL58S ERROR
[FP] fp_set_dimmer ERROR
[FP] DISP ON
[FP] DISP OFF
[FP_DIMMER]PIP_ERR=%d
[FP] BRIGHTNESS GET [ %d ]
[FP] BRIGHTNESS SET [ %d ]
```

**Established:** the firmware has a front-panel dimmer function, an error path
named for a CAN dimming value, and an error for **KL58s**. Terminal 58s is VW's
name for the dimmed instrument-lighting level. Display on/off and brightness
get/set sit next to it.

### 5.2.1 Traced: CAN `0x635` → panel frame `ADDR 0x06`

Traced in Ghidra on V574 `OSM` at 0x80400200. **This is V574 firmware. Whether
the bench unit runs it is unchecked.** The function names are the labels saved
in the Ghidra project (§6), not names taken from the firmware.

**1. Registration — established.** `dim_register_0x635` (0x8060431A), called
from `dim_init`, fills a descriptor and passes it to `can_rx_register`
(0x80665F94). That is the general CAN receive-registration routine; it has
about 30 callers.

```
8060431e  mov.w  0x806044a8,r0     ; r0 = 0x0635
80604326  mov.w  r0,@(0x2,r5)      ; desc.id       = 0x635
8060432a  mov.l  r4,@(0x4,r5)      ; desc.callback = 0x8060463e
80604332  mov.l  r6,@(0x8,r5)      ; desc.buffer   = 0x8e9ede79
80604336  mov.w  r0,@(0xc,r5)      ; desc.len      = 3        (delay slot)
80604334  jsr    @r7               ; can_rx_register(handle, desc)
```

If `can_rx_register` returns −6, the code prints `fp_dim_can_error`.
**`0x635` is the dimming message, and it is 3 bytes long.**

**2. Receive callback — established.** `dim_can_rx_0x635` (0x8060463E) gets
the data in `r6`. It:
- sets the "dimming received" flags (state+0x0A = 1, state+0x0B = 0);
- copies byte 0 → state+0x14 and byte 1 → state+0x15;
- passes byte 1 to `dim_check_kl58s`. If byte 1 > 0x7E, that prints
  `KL58S ERROR` and bumps an error counter (state+0x0E, capped at 5).

Byte 2 is not read anywhere on this path. **Byte 1 is the KL58s value.**

**3. Validation — established.** `dim_sanitize` (0x80604874) takes the raw
bytes:

| byte | valid range | when invalid |
|---|---|---|
| 0 | 0x06–0x7E | the last good value, or 0x50 if a flag is set |
| 1 (KL58s) | 0x00–0x7E | 0x50, 0, or the last good value, depending on flags |

Valid values are saved as the new last-good value. The result goes to
`dim_set_levels` (state+0x17 and +0x18). The curve functions further down
clamp both values to **100**, so the usable range is 0x00–0x64. That matches
the third-party description in `CANBUS.md` §3.

**4. Levels → three PWM values — established in structure, curves not
evaluated.**
- `dim_curve_display` (0x806051F6) maps byte 0 (0–100) to 0–0x9B0.
- `dim_curve_ab` (0x80605030) gives one value from byte 0 × 10 and another
  from byte 1.

So byte 0 drives two values and byte 1 drives one. The piecewise constants are
in the image, but the decompiler dropped some blocks, so I have not written
out the curves.

**5. Panel frame — established.** `fp_set_dimmer` → `fp_send_dim_frame`
(0x8060530C) takes a 0x20-byte buffer from the front-panel TX pool
(`fp_txbuf_alloc`, the source of `[FP] GET ERROR`) and builds:

```
06 0E  A  B'  C  A'  B  C'  CK

A  = from byte 0 (dim_curve_ab)      A' = 0x158E − A
B  = dim_curve_display(byte 0)       B' = 0x09B0 − B
C  = from byte 1 (dim_curve_ab)      C' = 0x3070 − C
each value u16 big-endian;  CK = (sum of the 14 preceding bytes) & 0xFF
```

The checksum routine (`fp_checksum`, 0x8060360E) adds up LEN bytes starting
at ADDR. **That is exactly the `[ADDR][LEN][payload][CKSUM]` format of
`PROTOCOL.md` §2**: ADDR 0x06, LEN 0x0E, 12 payload bytes. The frame is posted
to mailbox 0x14. `fp_set_dimmer` only sends when the values have changed
(`FUN_806052D0` keeps the last frame's values).

**Inference:** mailbox 0x14 belongs to `FPDRV_TSK`, which puts the frame on the
9-pin link. Each value is sent alongside its complement against a fixed
period (0x158E, 0x09B0, 0x3070), which looks like duty/period pairs for three
of the MB90561A's PPG timers. That fits `BACKLIGHT.md`'s suspicion of the
unused PPG channels. **`ADDR 0x06` has never been seen on the wire.** All
captures so far were panel → head unit, and `PROTOCOL.md` §3 lists only 0x0C,
0x0D, 0x0F and 0x18. This is the first head-unit → panel command identified,
and it can be sent from the Arduino directly, without CAN.

### 5.3 Power management and ignition

```
Now skon[%d] Now Kl15[%d]
PWM CAN_Pass_mzas mZas[%02x]
CAN_Pass_mzas() Error!! [%02x]
>>>>>>>> PWM mZas CAN ID A3!!
>>>>>>>> VCL mZas CAN ID A3!!
PWM_Can_Awake( UBYTE ModuleAdr ) [%d]
PWM_Can_Sleep( UBYTE ModuleAdr ) [%d][%d]
@@@@@@@@@@@@@@@@@@@@@@ PWM_CAN_BUS_SLEEP_FROM_CAN =
T_SLEEPINDICATION_WAIT
```

**Inference:** here "PWM" means a power-manager module, not pulse-width
modulation. It reads `mZAS` (the ignition-switch message), separates the S
contact (key inserted) from KL15 (ignition on), and handles CAN wake and sleep.
`CANBUS.md` §4 found that a bench unit sends NM traffic but no application
frames. A power manager that waits for a valid `mZAS` frame before starting the
application would explain that. **Unverified:** neither the frame layout nor
the condition it checks is known yet.

### 5.4 Messages to the cluster

```
[CAN_SendMessage] LC_MRADIO1 Err (%d) !!
[CAN_SendMessage] LC_MRADIO2 Err (%d) !!
MRADIO4 ON1 / OFF1 / ON2 / OFF2
KMB_ERROR mRADIO1 %d
[KMB] car_model = %x
ADC_SETCALLBACK ERROR by KOMBI!!
```

`mRadio_1/2/4` are the messages the head unit sends, and "KMB" is the Kombi
(instrument cluster). `[KMB] car_model` suggests the unit reads the vehicle
type from the cluster.

Other CAN infrastructure strings: `CAN_MainTask`, `CAN_TXRING_OVER` (loader);
`[CAN]Can RingBuffer Overflow`, `[CAN]CAN_TpOpn is called!!` (a transport
protocol), `TELCAN_TSK`, `[RVC] CAN` (OSM); `AMI_BAPERR_LOG` (BAP).

### 5.5 The panel link from the head unit's side

Traced in Ghidra on V574 `OSM`, like §5.2.1. Names are the labels saved by
`ghidra/LabelFp.java`. **Everything in this section comes from disassembly.
None of it has been sent to a panel yet.**

**Link layer — established.** The FPDRV task near 0x80555000 owns the UART.

- **ACK.** For every valid panel frame, `fpdrv_send_ack` (0x805556DC) sends
  the bare byte **`0x15`**. If the head unit has a frame queued, it sends
  **`0x16` followed by that frame** instead, so the ACK and the next command go
  out together.
- **The head unit expects the same from the panel.** In `fpdrv_rx_loop`
  (0x80555424), a received `0x15` is treated as the ACK of the last frame sent,
  and a received `0x18` frame as a NAK, which leads to a retransmit.
- **Timeout.** Every frame except bare `0x15`/`0x18` starts a 300 ms reply
  timer. After 3 failures the head unit sends `00 03 2E 31`
  (`fpdrv_send_resync`). If that also fails, it hard-resets the panel. This is
  the `[FPDRV] fpdrv hard reset` string.
- **NAK.** `fpdrv_send_nak` sends `18 03 <flags> CK`. The flags come from
  `fpdrv_rx_validate` (0x80556B68):

  | flag | meaning on the head-unit side |
  |---|---|
  | `0x01` | checksum wrong |
  | `0x04` | ADDR is one the panel must not send (see below), or ≥ 0x13 |
  | `0x40` | LEN does not match the table below |
  | `0x80` | valid frame, but no handler for its ADDR (`fpdrv_rx_dispatch`) |

**Panel → head unit — established.** The validator's length table, together
with the dispatcher:

| ADDR | LEN | head unit does |
|---|---|---|
| `0x04` | any | ACKs, then ignores it (the handler is a bare `rts`) |
| `0x08` | 6 | ACKs only |
| `0x0B` | 3 | ACKs only |
| `0x0C` | 8 | key bitmap → UI task (`fp_rx_keys_0C`) |
| `0x0D` | 6 | rotary → UI task |
| `0x0F` | 2 | ACK, then starts the init sequence below |
| `0x10` | 3 | ACKs and logs it |
| `0x11` | 3 | ACKs only |
| `0x12` | any | ACKs only |
| `0x18` | 3 | NAK of the head unit's last frame → retransmit |

**Head unit → panel — established.** The validator rejects these as panel
addresses, which makes them the head unit's command set:
`00 01 02 03 06 07 09 0A 0E`.

| ADDR | frame | sent when |
|---|---|---|
| `0x00` | `00 03 2E 31` | resync, after 3 timeouts |
| `0x01` | `01 06 00 28 08 03 3A` | builder exists, **no caller found** |
| `0x02` | `02 0C 40 1D 4B 42 40 00 40 01 FF 05 7D` | init step 0 |
| `0x03` | `03 0F 3C 0A 02 0A 04 0A 04 0A 04 0A 04 0A 0A A6` | init step 1 |
| `0x0A` | `0A 07 00 FF 1C FF 1C 47` | init step 2 |
| `0x09` | `09 06 00 00 0F 06 24` | init step 3 |
| `0x06` | `06 0E 00 00 00 00 30 70 00 00 00 00 00 00 B4` | init step 4; afterwards the dimmer (§5.2.1) |
| `0x07` | `07 06 o0 o1 o2 o3 CK` | lamps, §5.6 |
| `0x0E` | — | accepted as a command address, **nothing in this OSM builds it** |

**Init sequence — established.** `fpdrv_init_step` (0x805567DE) is a switch on
a step counter. Each `0x15` from the panel advances it:

```
panel  0F 02 11                      boot announcement
HU     15                            ACK
HU     02 0C …  7D    panel 15
HU     03 0F …  A6    panel 15
HU     0A 07 …  47    panel 15
HU     09 06 …  24    panel 15
HU     06 0E …  B4    panel 15       init done
```

What the payloads of `0x02`, `0x03`, `0x09` and `0x0A` configure is not known.
**Inference:** `0x03` (`3C 0A 02 0A 04 0A …`) looks like timing parameters,
perhaps key repeat or debounce.

### 5.6 Softkey indicator lamps — `ADDR 0x07`

**Frame — established.** `fp_send_lamp_frame` (0x80603056) takes a 32-bit
lamp word and splits it by bit parity:

```
07 06  o0 o1  o2 o3  CK

o2:o3 (u16 BE) bit k = lamp word bit 2k      (the even bits)
o0:o1 (u16 BE) bit k = lamp word bit 2k+1    (the odd bits)
CK = (sum of the 6 preceding bytes) & 0xFF
```

It goes through the same TX pool and mailbox 0x14 as the dimmer frame.

**Lamp word — established.** `lamp_update` (0x8059A840) sets even bits only,
so in this firmware **`o0` and `o1` are always zero**:

| lamp word bit | `o2`/`o3` bit | on when |
|---|---|---|
| 0, 2 | `o3` `0x01`, `0x02` | the CD-mechanism state (`FUN_80602e2c`, next to the `CDS_Eject` code) is not 2 |
| **4** | **`o3` `0x04`** | **softkey mask bit 0**, and the power state is 3 |
| **6** | **`o3` `0x08`** | **softkey mask bit 1**, and the power state is 3 |
| **8** | **`o3` `0x10`** | **softkey mask bit 2**, and the power state is 3 |
| **10** | **`o3` `0x20`** | **softkey mask bit 3**, and the power state is 3 |
| 12, 14 | `o3` `0x40`, `0x80` | byte 0 of the dimmer state (the struct `0x635` fills) is 1 |
| 16 | `o2` `0x01` | same as above |

If `lamp_power_ok` fails (the power manager is not in state 2 or 3, plus two
other state checks), the frame is still sent, with every lamp off.

**Where the mask comes from — established.** On every screen change, the
transition handler (0x805B55B0) calls `screen_softkey_lamp(new_screen)`. That
looks the screen up in a table at **0x8046B0C0**: 221 entries of
`{u16 screen_id, u16 mask}`. If the mask differs from the last one and is not
`0xF`, it is stored and the lamp frame is rebuilt.

| mask | screens |
|---|---|
| `0` (all off) | 141 |
| `0x1` | 2 (`0x04`, `0x24`) |
| `0x2` | 26 (mostly `0xA5`–`0xB8`, `0xD3`–`0xD8`) |
| `0x4` | 27 (`0x0E`–`0x23` and others) |
| `0x8` | 22 |
| `0xF` (leave unchanged) | 3 (`0x37`, `0x41`, `0x42`) |

Screens `0x6D` and `0x6E` work it out at run time from a state byte:
1 → `0x2`, 3 → `0x8`, 6 → `0x1`, anything else → `0`.

**At most one bit is ever set.** That matches what the panel shows: entering a
softkey's sub-screen lights that softkey's segment, and the main screens (mask 0)
turn all four off. Which bit is which corner has **not** been established.
The UI's key codes are known from a debug switch (0x805FAD78): `SKNW=5`,
`SKNE=6`, `SKSW=7`, `SKSE=8`, `SETUP=0x0F`, `RETURN=0x10`, `ROT_L/R=0x11/0x12`.
The table that turns the `0x0C` bitmap into those codes was not found in
`OSM`. Two bench frames settle it (§6).

## 6. Where to go next

Ghidra 12.1.4 is installed locally. It has the `SuperH4:BE:32:default` and
`V850:LE:32:default` language definitions.

The Ghidra project is at `~/ghidra_projects/rnse` on the host (outside the
repo; Ghidra refuses paths with a `.` element, which rules out the distrobox
home). It holds V574 `OSM` imported as `SuperH4:BE` at 0x80400200, fully
analysed, with the §5.2.1, §5.5 and §5.6 functions named. Helper scripts are
in this repo's `ghidra/` (pass it to Ghidra as `-scriptPath`): `Dump.java`,
`DumpRange.java`, `DumpRangeCreate.java` (creates functions at every prologue
first), `Listing.java`, `DisList.java` (forces
disassembly, for switch cases that auto-analysis missed), `Callers.java`,
`Label.java` and `LabelFp.java`.

1. ~~Find where the SH modules load.~~ Done (§3.3).
2. ~~Find the CAN handler behind the dimmer.~~ Done (§5.2.1): `0x635`, 3 bytes;
   byte 0 is display, byte 1 is KL58s.
3. **Bench test: send an `ADDR 0x06` frame from the Arduino.** Choose A, B and
   C, fill in the complements, add the checksum, and send it after the boot
   handshake. If the backlight responds, that closes `PROTOCOL.md` open
   question 14 without any CAN. Mid-range values (about half of each period)
   are the safe first try.
4. **Evaluate the curves** in `dim_curve_display` and `dim_curve_ab` (from the
   disassembly, not the decompiler output), so that real `0x635` values can be
   turned into exact frames. Then check them against a capture once a head
   unit runs.
5. **Follow `CAN_Pass_mzas`** to find what the power manager wants from `mZAS`
   before it starts the application. That is the precondition for `CANBUS.md`
   T6.
6. **Bench test: the panel link from §5.5–§5.6.** After `0F 02 11`, send `15`
   and then the five init frames, waiting for a `15` after each. Then:
   - `07 06 00 00 00 04 11` → lights the segment for softkey mask bit 0;
   - `07 06 00 00 00 08 15`, `… 10 1D`, `… 20 2D` → bits 1, 2, 3;
   - `07 06 00 00 00 00 0D` → all off.

   Record which corner each one lights; that closes the mapping in §5.6. Also
   worth trying: lamps 0/1/6/7/8 (`o3` `0x01`, `0x02`, `0x40`, `0x80`; `o2`
   `0x01`), and an odd bit (`o1` `0x04`) to see whether the odd half does
   anything, such as blinking. If `0x07` does nothing without the init frames,
   that also says the init matters.
7. Load the `.MOT` image as `V850:LE:32` at base 0x3800. This matters less now,
   but it would show what the V850 actually owns.

Before relying on any of this for the bench unit, check which hardware version
(V220/V574/VB48) it is.
