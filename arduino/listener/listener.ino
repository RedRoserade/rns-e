// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
//
// RNS-E front panel listener.
//
// Brings the board up properly, decodes its messages, and streams them to the
// PC over USB. Optionally sends an acknowledgement back to the panel.
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
//   1 VCC(+5V)  2 GND  3 RX  4 TX  5 PPG1  6 reset  7 power btn  8,9 backlight
//
//   D2  <- panel TX      (pin 4, input)
//   D3  -> panel RX      (pin 3, output)
//   D8  -> panel reset   (pin 6, active LOW: board runs high, stops low)
//   GND <-> panel GND    (pin 2) REQUIRED
//
// Reset wants a 15-30k pull-up in normal use. OMIT IT HERE: with the resistor
// in place the Arduino cannot assert reset cleanly and the board never comes
// up properly. Pins 7-9 are not on the serial bus at all -- the power/mute
// button just grounds pin 7, and 8/9 go to the backlight driver IC.
//
// Serial to PC: 115200 8N1.
//
// ---------------------------------------------------------------------------
// Serial commands (single characters)
// ---------------------------------------------------------------------------
//   r   reset the panel (low, pause, high)
//   a   toggle ACK sending
//   s   print status
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
// input until it receives this byte, at which point it goes quiet and enters
// normal edge-driven operation. A single bare byte -- no framing needed, and
// the panel sends no reply. Set to 0 to skip the handshake.
#define HANDSHAKE_BYTE   0x15
#define HANDSHAKE_WAIT_MS 500       // let it start announcing first

// Send an ACK after each well-formed message. GUESS -- see ack_for() below.
#define ACK_DEFAULT   0

// A message is considered complete after this much line silence.
#define MSG_IDLE_US   3000

#define MAXMSG        32

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
static unsigned long msgCount = 0, errCount = 0;

// ------------------------------------------------------------ software UART --

// Receive one 8E1 frame. Call with the line already at the start-bit falling
// edge. Returns false on a glitch, a parity error or a bad stop bit.
static bool panel_read_frame(uint8_t *out, bool *parity_ok, bool *framing_ok) {
  delayMicroseconds(HALFBIT_US);
  if (RX_HIGH()) return false;               // glitch, not a real start bit

  uint8_t v = 0;
  for (uint8_t i = 0; i < 8; i++) {
    delayMicroseconds(BIT_US - BIT_ADJ_RX);
    if (RX_HIGH()) v |= (1 << i);            // LSB first
  }
  delayMicroseconds(BIT_US - BIT_ADJ_RX);
  uint8_t p = RX_HIGH() ? 1 : 0;

  delayMicroseconds(BIT_US - BIT_ADJ_RX);
  uint8_t stop = RX_HIGH() ? 1 : 0;

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

static uint8_t  msg[MAXMSG];
static bool     msgParity[MAXMSG];
static uint8_t  msgLen = 0;

static uint8_t checksum(const uint8_t *b, uint8_t n) {
  uint16_t s = 0;
  for (uint8_t i = 0; i < n; i++) s += b[i];
  return (uint8_t)(s & 0xFF);
}

// Build the acknowledgement for a received message.
//
// GUESS. The panel repeats every message exactly 4 times and then gives up,
// which looks like an unacknowledged retry, but the ACK format has never been
// observed -- we have only ever seen the panel talk, never the head unit.
// The shape used here mirrors the only bare message form seen on the wire
// (0F 02 11: ADDR, LEN=2, checksum, no payload), addressed back to whatever
// sent it. If the retry count does not drop below 4, try other shapes here.
static uint8_t ack_for(const uint8_t *m, uint8_t n, uint8_t *out) {
  (void)n;
  out[0] = m[0];            // same ADDR
  out[1] = 0x02;            // LEN = 2, no payload
  out[2] = checksum(out, 2);
  return 3;
}

static void report(const uint8_t *m, uint8_t n, bool parityClean) {
  bool lenOk = (n >= 3) && ((m[1] + 1) == n);
  bool ckOk  = (n >= 3) && (checksum(m, n - 1) == m[n - 1]);

  Serial.print("MSG ");
  Serial.print(millis());
  Serial.print(' ');
  for (uint8_t i = 0; i < n; i++) {
    if (m[i] < 0x10) Serial.print('0');
    Serial.print(m[i], HEX);
    if (i + 1 < n) Serial.print(' ');
  }
  Serial.print(lenOk ? " LEN=ok" : " LEN=BAD");
  Serial.print(ckOk ? " CK=ok" : " CK=BAD");
  Serial.print(parityClean ? " PAR=ok" : " PAR=BAD");
  Serial.println();

  msgCount++;
  if (!lenOk || !ckOk || !parityClean) errCount++;

  if (ackEnabled && lenOk && ckOk && parityClean) {
    uint8_t a[8];
    uint8_t an = ack_for(m, n, a);
    panel_write(a, an);
    Serial.print("ACK ");
    for (uint8_t i = 0; i < an; i++) {
      if (a[i] < 0x10) Serial.print('0');
      Serial.print(a[i], HEX);
      if (i + 1 < an) Serial.print(' ');
    }
    Serial.println();
  }
}

// -------------------------------------------------------------------- misc --

static void reset_panel() {
  Serial.println("# reset: holding low");
  digitalWrite(PIN_RESET, LOW);
  delay(RESET_HOLD_MS);
  digitalWrite(PIN_RESET, HIGH);
  Serial.println("# reset: released, board announcing 0F 02 11");

#if HANDSHAKE_BYTE
  // Without this the panel stays in the announce phase forever, flooding the
  // log at 52.6 ms and ignoring every key press.
  delay(HANDSHAKE_WAIT_MS);
  msgLen = 0;                       // drop any partial announcement
  panel_write_byte(HANDSHAKE_BYTE);
  Serial.print("# handshake: sent 0x");
  Serial.println(HANDSHAKE_BYTE, HEX);
#endif

  delay(BOOT_MS);
  msgLen = 0;
  Serial.println("# ready (panel is silent until something changes)");
}

static void help() {
  Serial.println("# commands: r=reset  a=toggle ack  s=status  ?=help");
}

static void status() {
  Serial.print("# ack=");    Serial.print(ackEnabled ? "on" : "off");
  Serial.print(" messages="); Serial.print(msgCount);
  Serial.print(" errors=");   Serial.println(errCount);
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
      case 'r': msgLen = 0; reset_panel(); break;
      case 'a': ackEnabled = !ackEnabled; status(); break;
      case 's': status(); break;
      case '?': help(); break;
      default: break;
    }
  }

  // Poll for a start bit. Nothing else is time-critical, so a tight poll is
  // more reliable here than an interrupt.
  if (!RX_HIGH()) {
    uint8_t v; bool pok, fok;
    if (panel_read_frame(&v, &pok, &fok)) {
      if (msgLen < MAXMSG) {
        msg[msgLen] = v;
        msgParity[msgLen] = pok && fok;
        msgLen++;
      }
    }
    // wait out the stop bit so we do not re-trigger on the same frame
    while (!RX_HIGH()) { }
    return;
  }

  // A gap on an idle line ends the message.
  if (msgLen) {
    unsigned long t0 = micros();
    while (RX_HIGH()) {
      if (micros() - t0 > MSG_IDLE_US) {
        bool clean = true;
        for (uint8_t i = 0; i < msgLen; i++) clean &= msgParity[i];
        report(msg, msgLen, clean);
        msgLen = 0;
        break;
      }
      if (Serial.available()) break;       // let commands through
    }
  }
}
