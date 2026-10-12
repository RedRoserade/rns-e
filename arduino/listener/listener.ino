// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
//
// RNS-E front panel listener.
//
// Brings the board up properly, decodes its messages, and streams them to the
// PC over USB. Can play the head unit's side of the link as traced in its
// firmware (docs/FIRMWARE.md §5.5): the init frames after the boot
// announcement, and ACK/NAK for the panel's messages. Controls the lighting
// with the head unit's two frames (docs/PROTOCOL.md §8): the lamps (ADDR 0x07),
// which switch the button backlight and the indicators on and off, and the
// dimmer (ADDR 0x06), which sets their brightness. Can also send any raw frame.
//
// ---------------------------------------------------------------------------
// Why the board link is bit-banged
// ---------------------------------------------------------------------------
// The Uno has one hardware UART and it is shared with the USB bridge on D0/D1.
// If the panel sat there, every debug line we printed would also be delivered
// to the panel as input -- accidental fuzzing. So the panel gets a software
// UART on D2/D3 and the hardware Serial stays dedicated to the PC.
//
// SoftwareSerial cannot be used: it is 8N1 only, and the panel needs 8E1.
//
// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------
// The panel connector is a 9-pin Molex PicoBlade, 1.25 mm pitch:
//   1 VCC(+5V)  2 GND  3 RX  4 TX  5 PPG1  6 reset  7 power btn
//   8 rail monitor (out, +9V / 2)  9 LED rail (in, +9V)
//
//   D2  <- panel TX      (pin 4, input)
//   D3  -> panel RX      (pin 3, output)
//   D8  -> panel reset   (pin 6, active LOW: board runs high, stops low)
//   GND <-> panel GND    (pin 2) REQUIRED
//   +9V  -> panel pin 9  from a separate supply (a PP3 will do), NOT the
//           Arduino. Without it nothing lights. NEVER put 9 V on pin 1.
//
// Reset wants a 15-30k pull-up in normal use. OMIT IT HERE: with the resistor
// in place the Arduino cannot assert reset cleanly and the board never comes
// up properly. Pins 7-9 are not on the serial bus at all -- the power/mute
// button just grounds pin 7, pin 9 feeds every LED on the panel, and pin 8
// reports half of it back (docs/BACKLIGHT.md).
//
// Serial to PC: 115200 8N1.
//
// ---------------------------------------------------------------------------
// Serial commands (single characters)
// ---------------------------------------------------------------------------
//   r   reset the panel (low, pause, high)
//   a   toggle the link layer: ACK/NAK the panel, retransmit until ACKed
//   i   toggle the init frames after the boot announcement (applies on `r`)
//   s   print status
//   b   toggle the button backlight (lamp bit 0x0040), send the lamp frame
//   +   brightness up one step (doubles the on-time), send the dimmer frame
//   -   brightness down one step (halves the on-time), send the dimmer frame
//   l   resend the lamp and dimmer frames as they stand
//   L ON [FLASH]<newline>
//       set the lamp masks and send. Hex, bits as in the table below, e.g.
//       `L 44` = backlight + NE, `L 44 4` = the same with NE flashing
//   D A B C<newline>
//       set the raw dimmer values and send. Decimal or 0x hex. B and C are
//       OFF-times: 0 is full brightness, the period is off. e.g. `D 0 0 0x2800`
//   F ADDR LEN payload...<newline>
//       send a raw frame, hex bytes, checksum appended, e.g.
//       `F 07 06 00 00 00 40`
//
// Lamp bits (docs/PROTOCOL.md §8), the same in the ON and FLASH masks:
//   0x0001 SD/eject daughter board   0x0002 eject button
//   0x0004 NE   0x0008 NW   0x0010 SE   0x0020 SW   (brightness: channel B)
//   0x0040 button backlight                         (brightness: channel C)
// A flash bit flashes its lamp whether or not the ON bit is set.
//   ?   help

#include <Arduino.h>
#include <util/atomic.h>

// ------------------------------------------------------------------ config --

#define PIN_RX        2      // from panel TX
#define PIN_TX        3      // to panel RX
#define PIN_RESET     8      // active low

#define PC_BAUD       115200UL
#define PANEL_BAUD    9600UL

#define RESET_HOLD_MS 500
#define BOOT_MS       1000

// After reset the panel broadcasts `0F 02 11` every 52.6 ms and ignores all
// input until it receives an ACK, at which point it goes quiet and enters
// normal edge-driven operation (docs/PROTOCOL.md §7).
#define ANNOUNCE_WAIT_MS 1000       // give up waiting for `0F 02 11` after this

// Link layer, from the head unit's firmware (docs/FIRMWARE.md §5.5):
//   0x15        bare ACK, both directions
//   0x16        ACK with a frame following straight after
//   18 03 F CK  NAK; F = 0x01 checksum, 0x04 address, 0x40 length
// Every frame except a bare ACK or a NAK waits up to 300 ms for an ACK, and is
// retransmitted on NAK or timeout, 3 tries in all. (After that the head unit
// sends the resync `00 03 2E 31` and then hard-resets the panel; we just give
// up and say so.)
#define ACK_BYTE         0x15
#define ACK_MORE_BYTE    0x16
#define NAK_ADDR         0x18
#define NAK_CK           0x01
#define NAK_ADDRESS      0x04
#define NAK_LEN          0x40
#define REPLY_TIMEOUT_MS 300
#define TX_TRIES         3

// ACK/NAK the panel's messages and retransmit our own until ACKed. Off: the
// old behaviour -- no replies, frames sent once (any reply is still logged).
#define ACK_DEFAULT   1

// Answer the boot announcement with the head unit's init sequence instead of
// a bare ACK. The head unit steps through these on each ACK from the panel;
// the last one is a dimmer frame with every channel at zero but C. All five
// are verbatim from the firmware, checksums included. That last frame leaves
// everything dark (B = B' = 0, C = full), so after it we send our own dimmer
// and lamp frames. Off: bare 0x15, which is the handshake the bench has
// always used.
#define INIT_DEFAULT  1

// What goes out before the first init frame. By the head unit's own ACK rule
// it would be 0x16 + the frame, but on the bench (2026-10-10) that puts the
// panel in state B: `18 03 80 9B` ~270 ms later, then every 53.6 ms, whatever
// follows. So a bare 0x15, which is proven to end the announcement, then a
// pause before the first frame. FIRMWARE.md §5.5 draws it this way too.
#define INIT_LEAD_BYTE   ACK_BYTE
#define INIT_LEAD_GAP_MS 20

static const uint8_t INIT_02[] = { 0x02, 0x0C, 0x40, 0x1D, 0x4B, 0x42, 0x40, 0x00,
                                   0x40, 0x01, 0xFF, 0x05, 0x7D };
static const uint8_t INIT_03[] = { 0x03, 0x0F, 0x3C, 0x0A, 0x02, 0x0A, 0x04, 0x0A,
                                   0x04, 0x0A, 0x04, 0x0A, 0x04, 0x0A, 0x0A, 0xA6 };
static const uint8_t INIT_0A[] = { 0x0A, 0x07, 0x00, 0xFF, 0x1C, 0xFF, 0x1C, 0x47 };
static const uint8_t INIT_09[] = { 0x09, 0x06, 0x00, 0x00, 0x0F, 0x06, 0x24 };
static const uint8_t INIT_06[] = { 0x06, 0x0E, 0x00, 0x00, 0x00, 0x00, 0x30, 0x70,
                                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xB4 };
static const uint8_t *const INIT_FRAMES[] = { INIT_02, INIT_03, INIT_0A, INIT_09, INIT_06 };
static const uint8_t INIT_LENS[] = { sizeof INIT_02, sizeof INIT_03, sizeof INIT_0A,
                                     sizeof INIT_09, sizeof INIT_06 };

// A message is considered complete after this much line silence.
#define MSG_IDLE_US   3000

#define MAXMSG        32

// ---------------------------------------------------------------- lighting --
// Two frames, from the head unit's firmware and mapped on the bench
// (docs/PROTOCOL.md §8). Every LED on the panel runs off connector pin 9.
//
// Lamps -- on/off. A 32-bit lamp word, each lamp a pair of bits (2k = on,
// 2k+1 = flash), split by parity into two u16 big-endian masks:
//
//   07 06  FLASH  ON  CK
//
// Dimmer -- brightness. Three PWM channels, each value u16 big-endian and
// sent with its complement against the channel's period:
//
//   06 0E  A  B'  C  A'  B  C'  CK      A' = PERIOD_A - A, ...
//
// B is the off-time of the corner indicators, C of the button backlight:
// 0 = full, the period = off. A had no visible effect. The eye is roughly
// logarithmic, so full and half look alike and all the visible change is at
// the bottom: on the bench the backlight was visible down to C' = 0x171 (3%)
// and gone at C' = 0x70. Hence +/- step by doubling and halving.
#define LAMP_ADDR     0x07
#define LAMP_BACKLIGHT 0x0040
#define LAMP_DEFAULT  LAMP_BACKLIGHT   // after init: backlight on, indicators off

#define DIM_ADDR      0x06
#define PERIOD_A      0x158E
#define PERIOD_B      0x09B0
#define PERIOD_C      0x3070

// Brightness steps: on-time = period >> (BRIGHT_MAX - level), level 0 = off.
// Level 4 is 1/32 of the period, the dimmest the bench could see.
#define BRIGHT_MAX    9
#define BRIGHT_DEFAULT BRIGHT_MAX

// -------------------------------------------------------------- bit timing --
// 9600 baud = 104.1667 us/bit. The constants below are the nominal values
// minus measured loop overhead. Sampling is mid-bit, so there is +/-52 us of
// slack per bit; if you see parity errors, nudge BIT_US by a microsecond.

#define BIT_US        104
#define BIT_ADJ_RX    3      // subtracted from each RX bit delay
#define BIT_ADJ_TX    4      // subtracted from each TX bit delay
#define HALFBIT_US    (BIT_US / 2)

// Direct port access: D2 and D3 are both on PORTD, so reads are one cycle.
#define RX_HIGH()     (PIND & _BV(PIN_RX))
#define TX_SET(v)     do { if (v) PORTD |= _BV(PIN_TX); else PORTD &= ~_BV(PIN_TX); } while (0)

static bool ackEnabled = ACK_DEFAULT;
static bool initEnabled = INIT_DEFAULT;
static const uint16_t dimPeriod[3] = { PERIOD_A, PERIOD_B, PERIOD_C };
static uint16_t dimVal[3] = { 0, 0, 0 };     // A, B, C: B and C at full
static uint8_t brightness = BRIGHT_DEFAULT;
static uint16_t lampOn = LAMP_DEFAULT, lampFlash = 0;
static unsigned long msgCount = 0, errCount = 0;

// ------------------------------------------------------------ software UART --

// Receive one 8E1 frame. Call with the line already at the start-bit falling
// edge. Returns false on a glitch, a parity error or a bad stop bit.
//
// Interrupts off, as for TX: the USB serial interrupt fires every ~87 us while
// a log line drains, and enough of those within one byte push the sampling
// past mid-bit. On the bench that turned the panel's 0x15 ACK into garbage
// whenever it arrived right after we had printed something.
static bool panel_read_frame(uint8_t *out, bool *parity_ok, bool *framing_ok) {
  uint8_t v = 0, p, stop;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    delayMicroseconds(HALFBIT_US);
    if (RX_HIGH()) return false;             // glitch, not a real start bit

    for (uint8_t i = 0; i < 8; i++) {
      delayMicroseconds(BIT_US - BIT_ADJ_RX);
      if (RX_HIGH()) v |= (1 << i);          // LSB first
    }
    delayMicroseconds(BIT_US - BIT_ADJ_RX);
    p = RX_HIGH() ? 1 : 0;

    delayMicroseconds(BIT_US - BIT_ADJ_RX);
    stop = RX_HIGH() ? 1 : 0;
  }

  uint8_t ones = p;
  for (uint8_t i = 0; i < 8; i++) if (v & (1 << i)) ones++;

  *out = v;
  *parity_ok = ((ones & 1) == 0);            // even parity
  *framing_ok = (stop == 1);
  return true;
}

// Transmit one 8E1 frame. Interrupts off: a stray ISR mid-frame corrupts it.
static void panel_write_byte(uint8_t v) {
  uint8_t ones = 0;
  for (uint8_t i = 0; i < 8; i++) if (v & (1 << i)) ones++;
  uint8_t p = (ones & 1);                    // even parity

  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    TX_SET(0);                               // start bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    for (uint8_t i = 0; i < 8; i++) {
      TX_SET(v & (1 << i));
      delayMicroseconds(BIT_US - BIT_ADJ_TX);
    }
    TX_SET(p);
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    TX_SET(1);                               // stop bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
  }
}

static void panel_write(const uint8_t *buf, uint8_t n) {
  for (uint8_t i = 0; i < n; i++) panel_write_byte(buf[i]);
}

// ---------------------------------------------------------------- messages --

static uint8_t checksum(const uint8_t *b, uint8_t n) {
  uint16_t s = 0;
  for (uint8_t i = 0; i < n; i++) s += b[i];
  return (uint8_t)(s & 0xFF);
}

static void print_hex(const uint8_t *b, uint8_t n) {
  for (uint8_t i = 0; i < n; i++) {
    if (b[i] < 0x10) Serial.print('0');
    Serial.print(b[i], HEX);
    if (i + 1 < n) Serial.print(' ');
  }
}

// Read one message. Call with the line at a start-bit edge; collects bytes
// until MSG_IDLE_US of silence. *clean is false if any byte had a parity or
// stop-bit error.
static uint8_t read_message(uint8_t *buf, bool *clean) {
  uint8_t n = 0;
  *clean = true;
  for (;;) {
    uint8_t v; bool pok, fok;
    if (panel_read_frame(&v, &pok, &fok)) {
      if (n < MAXMSG) buf[n++] = v;
      *clean &= pok && fok;
    }
    // wait out the stop bit so we do not re-trigger on the same frame
    while (!RX_HIGH()) { }
    unsigned long t0 = micros();
    while (RX_HIGH())
      if (micros() - t0 > MSG_IDLE_US) return n;
  }
}

// Wait up to timeout_ms for a message. Returns its length, 0 on timeout.
static uint8_t wait_message(uint8_t *buf, bool *clean, unsigned long timeout_ms) {
  unsigned long t0 = millis();
  while (millis() - t0 < timeout_ms)
    if (!RX_HIGH()) return read_message(buf, clean);
  return 0;
}

// Leading bare ACK bytes. The panel answers within ~1.2 ms, so an ACK and a
// frame of its own can land in the same message. 0x15 and 0x16 are never
// frame addresses (the head unit rejects anything >= 0x13).
static uint8_t count_acks(const uint8_t *m, uint8_t n) {
  uint8_t k = 0;
  while (k < n && (m[k] == ACK_BYTE || m[k] == ACK_MORE_BYTE)) k++;
  return k;
}

static void print_acks(const uint8_t *m, uint8_t k) {
  Serial.print("RX ");
  Serial.print(millis());
  Serial.print(' ');
  print_hex(m, k);
  Serial.println(k == 1 && m[0] == ACK_BYTE ? "  panel ACK" : "  panel ACK(s)");
}

// NAK flags for a message from the panel, as the head unit's validator
// (fpdrv_rx_validate) would set them. 0 = valid.
static uint8_t validate(const uint8_t *m, uint8_t n) {
  if (n < 3 || m[1] + 1 != n) return NAK_LEN;
  if (checksum(m, n - 1) != m[n - 1]) return NAK_CK;
  switch (m[0]) {
    case 0x00: case 0x01: case 0x02: case 0x03: case 0x06:
    case 0x07: case 0x09: case 0x0A: case 0x0E:
      return NAK_ADDRESS;                      // head-unit-only addresses
  }
  return (m[0] >= 0x13 && m[0] != NAK_ADDR) ? NAK_ADDRESS : 0;
}

static bool is_nak(const uint8_t *m, uint8_t n) {
  return n == 4 && m[0] == NAK_ADDR && validate(m, n) == 0;
}

// Print a message from the panel in the format map_buttons.py parses.
static void print_msg(const uint8_t *m, uint8_t n, bool parityClean) {
  bool lenOk = (n >= 3) && ((m[1] + 1) == n);
  bool ckOk  = (n >= 3) && (checksum(m, n - 1) == m[n - 1]);

  Serial.print("MSG ");
  Serial.print(millis());
  Serial.print(' ');
  print_hex(m, n);
  Serial.print(lenOk ? " LEN=ok" : " LEN=BAD");
  Serial.print(ckOk ? " CK=ok" : " CK=BAD");
  Serial.print(parityClean ? " PAR=ok" : " PAR=BAD");
  Serial.println();

  msgCount++;
  if (!lenOk || !ckOk || !parityClean) errCount++;
}

static void send_nak(uint8_t flags) {
  uint8_t f[4] = { NAK_ADDR, 0x03, flags, 0 };
  f[3] = checksum(f, 3);
  panel_write(f, sizeof f);
}

// Send a frame the way the head unit does: wait for the panel's ACK, and
// retransmit on NAK or timeout. `lead` (0 = none) goes out right before the
// first try only, for 0x16 + frame. With the link layer off, sends once and
// just logs whatever comes back. Returns true if ACKed.
static bool send_frame(const uint8_t *f, uint8_t n, uint8_t lead, const char *what) {
  uint8_t tries = ackEnabled ? TX_TRIES : 1;
  for (uint8_t t = 1; t <= tries; t++) {
    if (lead && t == 1) {
      panel_write_byte(lead);
      delay(INIT_LEAD_GAP_MS);
    }
    unsigned long t0 = millis();
    panel_write(f, n);

    // Listen before logging. The panel ACKs ~1 ms after the last byte, and a
    // TX line long enough to fill the USB serial buffer blocks for longer
    // than that, so printing first misses the ACK.
    uint8_t m[MAXMSG]; bool clean;
    uint8_t mn = wait_message(m, &clean, REPLY_TIMEOUT_MS);

    Serial.print("TX ");
    Serial.print(t0);
    Serial.print(' ');
    if (lead && t == 1) { print_hex(&lead, 1); Serial.print(" + "); }
    print_hex(f, n);
    Serial.print("  ");
    Serial.print(what);
    if (t > 1) { Serial.print(" (try "); Serial.print(t); Serial.print(')'); }
    Serial.println();

    for (;;) {
      if (!mn) {
        unsigned long elapsed = millis() - t0;
        if (elapsed >= REPLY_TIMEOUT_MS) {
          Serial.println("# no reply");
          break;
        }
        mn = wait_message(m, &clean, REPLY_TIMEOUT_MS - elapsed);
        continue;
      }
      uint8_t k = count_acks(m, mn);
      if (k) print_acks(m, k);
      if (k < mn) {
        if (is_nak(m + k, mn - k)) {
          Serial.print("RX ");
          Serial.print(millis());
          Serial.print(' ');
          print_hex(m + k, mn - k);
          Serial.println("  panel NAK");
          if (!k) break;                     // retransmit
        } else {
          print_msg(m + k, mn - k, clean);   // a frame of its own; not ACKed here
        }
      }
      if (k) return true;
      mn = 0;
    }
  }
  if (ackEnabled) {
    Serial.print("# gave up after ");
    Serial.print(tries);
    Serial.println(" tries");
  }
  return false;
}

static void send_dim();
static void send_lamps();

// The head unit's answer to `0F 02 11`: the init sequence, or a bare ACK.
static void answer_announce() {
  if (!initEnabled) {
    panel_write_byte(ACK_BYTE);
    Serial.println("ACK 15  (init off)");
    return;
  }
  for (uint8_t i = 0; i < sizeof INIT_LENS; i++) {
    char what[] = "init 0/5";
    what[5] = '1' + i;
    if (!send_frame(INIT_FRAMES[i], INIT_LENS[i], i == 0 ? INIT_LEAD_BYTE : 0, what)) {
      Serial.println("# init stopped");
      return;
    }
  }
  Serial.println("# init done");
  send_dim();
  send_lamps();
}

// A message from the panel outside any exchange of ours.
static void handle_message(const uint8_t *m, uint8_t n, bool clean) {
  uint8_t k = count_acks(m, n);
  if (k) print_acks(m, k);                   // nothing of ours was waiting
  m += k; n -= k;
  if (!n) return;

  // Reply first, log after: printing can block for longer than the panel
  // waits, as in send_frame().
  bool ack = false;
  uint8_t flags = 0;
  if (ackEnabled && clean && m[0] != 0x0F) { // UART error: drop it, the panel retries
    flags = validate(m, n);
    if (flags) send_nak(flags);
    else if (m[0] != NAK_ADDR) {             // the panel's NAK is never ACKed
      panel_write_byte(ACK_BYTE);
      ack = true;
    }
  }

  print_msg(m, n, clean);
  if (ack) Serial.println("ACK 15");
  if (flags) {
    Serial.print("NAK 18 03 ");
    if (flags < 0x10) Serial.print('0');
    Serial.println(flags, HEX);
  }
  if (ackEnabled && clean && m[0] == NAK_ADDR && !flags)
    Serial.println("# panel NAK, nothing to retransmit");
  if (ackEnabled && clean && m[0] == 0x0F && validate(m, n) == 0)
    answer_announce();
}

static void put_u16(uint8_t *p, uint16_t v) {
  p[0] = v >> 8;
  p[1] = v & 0xFF;
}

static void send_dim() {
  uint8_t f[15];
  f[0] = DIM_ADDR;
  f[1] = 0x0E;                               // LEN: 12 payload bytes
  put_u16(&f[2],  dimVal[0]);
  put_u16(&f[4],  PERIOD_B - dimVal[1]);
  put_u16(&f[6],  dimVal[2]);
  put_u16(&f[8],  PERIOD_A - dimVal[0]);
  put_u16(&f[10], dimVal[1]);
  put_u16(&f[12], PERIOD_C - dimVal[2]);
  f[14] = checksum(f, 14);

  char what[40];
  snprintf(what, sizeof what, "A=0x%X B=0x%X C=0x%X", dimVal[0], dimVal[1], dimVal[2]);
  send_frame(f, sizeof f, 0, what);
}

// Step B and C together, one brightness level up or down. A is left alone.
static void step_brightness(int8_t dir) {
  if ((dir < 0 && brightness == 0) || (dir > 0 && brightness == BRIGHT_MAX)) {
    Serial.println(dir < 0 ? "# already off" : "# already at full");
    return;
  }
  brightness += dir;
  for (uint8_t i = 1; i < 3; i++) {
    uint16_t on = brightness ? dimPeriod[i] >> (BRIGHT_MAX - brightness) : 0;
    dimVal[i] = dimPeriod[i] - on;
  }
  Serial.print("# brightness ");
  Serial.print(brightness);
  Serial.print('/');
  Serial.println(BRIGHT_MAX);
  send_dim();
}

static void send_lamps() {
  uint8_t f[7];
  f[0] = LAMP_ADDR;
  f[1] = 0x06;                               // LEN: 4 payload bytes
  put_u16(&f[2], lampFlash);
  put_u16(&f[4], lampOn);
  f[6] = checksum(f, 6);

  char what[32];
  snprintf(what, sizeof what, "lamps on=0x%X flash=0x%X", lampOn, lampFlash);
  send_frame(f, sizeof f, 0, what);
}

// `L ON [FLASH]`: the L has been read; parse the rest of the line.
static void read_lamp_line() {
  char line[24];
  uint8_t n = Serial.readBytesUntil('\n', line, sizeof line - 1);
  line[n] = '\0';
  char *end;
  unsigned long on = strtoul(line, &end, 16);
  if (end == line || on > 0xFFFF) {
    Serial.println("# usage: L ON [FLASH]   (hex masks, e.g. L 44)");
    return;
  }
  char *p = end;
  unsigned long flash = strtoul(p, &end, 16);
  if (end == p) flash = 0;
  else if (flash > 0xFFFF) {
    Serial.println("# usage: L ON [FLASH]   (hex masks, e.g. L 44 4)");
    return;
  }
  lampOn = on;
  lampFlash = flash;
  send_lamps();
}

// `D A B C`: the D has been read; parse the rest of the line.
static void read_dim_line() {
  char line[40];
  uint8_t n = Serial.readBytesUntil('\n', line, sizeof line - 1);
  line[n] = '\0';
  char *p = line;
  uint32_t v[3];
  for (uint8_t i = 0; i < 3; i++) {
    char *end;
    v[i] = strtoul(p, &end, 0);
    if (end == p) {
      Serial.println("# usage: D A B C   (decimal or 0x hex)");
      return;
    }
    p = end;
  }
  for (uint8_t i = 0; i < 3; i++) {
    if (v[i] > dimPeriod[i]) {
      Serial.print("# capped to period: ");
      Serial.println(dimPeriod[i]);
      v[i] = dimPeriod[i];
    }
    dimVal[i] = v[i];
  }
  send_dim();
}

// `F ADDR LEN payload...`: the F has been read; parse hex bytes to the end of
// the line, append the checksum and send. LEN is taken as typed, not checked,
// so malformed frames can be sent on purpose.
static void read_raw_line() {
  char line[3 * MAXMSG + 8];
  uint8_t n = Serial.readBytesUntil('\n', line, sizeof line - 1);
  line[n] = '\0';
  uint8_t f[MAXMSG];
  uint8_t k = 0;
  char *p = line;
  for (;;) {
    char *end;
    unsigned long v = strtoul(p, &end, 16);
    if (end == p) break;
    if (k == MAXMSG - 1 || v > 0xFF) {
      Serial.println("# frame too long, or a byte over FF");
      return;
    }
    f[k++] = v;
    p = end;
  }
  if (k < 2) {
    Serial.println("# usage: F ADDR LEN payload...   (hex, checksum appended)");
    return;
  }
  f[k] = checksum(f, k);
  send_frame(f, k + 1, 0, "raw");
}

// -------------------------------------------------------------------- misc --

static void reset_panel() {
  Serial.println("# reset: holding low");
  digitalWrite(PIN_RESET, LOW);
  delay(RESET_HOLD_MS);
  digitalWrite(PIN_RESET, HIGH);
  Serial.println("# reset: released, waiting for 0F 02 11");

  // Answer right after an announcement, not into the middle of one. Without
  // an answer the panel stays in the announce phase forever, flooding the
  // log at 52.6 ms and ignoring every key press.
  uint8_t m[MAXMSG]; bool clean;
  unsigned long t0 = millis();
  for (;;) {
    unsigned long elapsed = millis() - t0;
    if (elapsed >= ANNOUNCE_WAIT_MS) {
      Serial.println("# no announcement seen; answering anyway");
      break;
    }
    uint8_t n = wait_message(m, &clean, ANNOUNCE_WAIT_MS - elapsed);
    if (n == 3 && m[0] == 0x0F && m[1] == 0x02 && m[2] == 0x11) break;
    if (n) print_msg(m, n, clean);
  }
  answer_announce();

  // Log, but do not answer, whatever repeats were already on their way.
  t0 = millis();
  while (millis() - t0 < BOOT_MS) {
    uint8_t n = wait_message(m, &clean, BOOT_MS - (millis() - t0));
    if (n) print_msg(m, n, clean);
  }
  Serial.println("# ready (panel is silent until something changes)");
}

static void help() {
  Serial.println("# commands: r=reset  a=toggle ack/nak  i=toggle init  s=status  ?=help");
  Serial.println("# lights: b=backlight on/off  +/-=brightness  l=resend");
  Serial.println("#   L ON [FLASH]  lamps, hex: 1 SD/eject 2 eject 4 NE 8 NW 10 SE 20 SW 40 backlight");
  Serial.println("#   D A B C  raw dimmer (B, C = off-time: 0 full, period off)");
  Serial.println("# raw: F ADDR LEN payload (hex, CK added), e.g. F 07 06 00 00 00 40");
}

static void status() {
  Serial.print("# ack=");    Serial.print(ackEnabled ? "on" : "off");
  Serial.print(" init=");    Serial.print(initEnabled ? "on" : "off");
  Serial.print(" messages="); Serial.print(msgCount);
  Serial.print(" errors=");   Serial.println(errCount);
  Serial.print("# lamps on=0x"); Serial.print(lampOn, HEX);
  Serial.print(" flash=0x");      Serial.println(lampFlash, HEX);
  Serial.print("# dim A=0x"); Serial.print(dimVal[0], HEX);
  Serial.print(" B=0x");      Serial.print(dimVal[1], HEX);
  Serial.print(" C=0x");      Serial.print(dimVal[2], HEX);
  Serial.print(" brightness="); Serial.print(brightness);
  Serial.print('/');          Serial.println(BRIGHT_MAX);
}

// -------------------------------------------------------------------- main --

void setup() {
  pinMode(PIN_RX, INPUT_PULLUP);
  pinMode(PIN_TX, OUTPUT);
  digitalWrite(PIN_TX, HIGH);            // idle high
  pinMode(PIN_RESET, OUTPUT);
  digitalWrite(PIN_RESET, LOW);          // hold stopped until we are ready

  Serial.begin(PC_BAUD);
  while (!Serial) { }
  Serial.println("# RNS-E listener  9600 8E1 on D2(rx)/D3(tx), reset D8");
  help();

  reset_panel();
}

void loop() {
  // PC commands
  if (Serial.available()) {
    switch (Serial.read()) {
      case 'r': reset_panel(); break;
      case 'a': ackEnabled = !ackEnabled; status(); break;
      case 'i': initEnabled = !initEnabled; status(); Serial.println("# applies on the next reset (r)"); break;
      case 's': status(); break;
      case 'b': lampOn ^= LAMP_BACKLIGHT; send_lamps(); break;
      case '+': step_brightness(+1); break;
      case '-': step_brightness(-1); break;
      case 'l': send_dim(); send_lamps(); break;
      case 'L': read_lamp_line(); break;
      case 'D': read_dim_line(); break;
      case 'F': read_raw_line(); break;
      case '?': help(); break;
      default: break;
    }
  }

  // Poll for a start bit. Nothing else is time-critical, so a tight poll is
  // more reliable here than an interrupt.
  if (!RX_HIGH()) {
    uint8_t m[MAXMSG]; bool clean;
    uint8_t n = read_message(m, &clean);
    if (n) handle_message(m, n, clean);
  }
}
