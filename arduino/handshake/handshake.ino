// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
//
// RNS-E front panel — dumb handshake probe.
//
// One job, no cleverness, no receiving, no decisions:
//
//     reset low -> reset high -> wait -> send REPLY[] -> wait -> repeat
//
// Everything is observed on the logic analyzer. The sketch never reads the
// panel and never decides anything, so there is no code path that can skip
// the transmit.
//
// ---------------------------------------------------------------------------
// Wiring -- identical to listener.ino and fuzzer.ino
// ---------------------------------------------------------------------------
// The panel connector is a 9-pin Molex PicoBlade, 1.25 mm pitch:
//   1 VCC(+5V)  2 GND  3 RX  4 TX  5 PPG1  6 reset  7 power btn  8,9 backlight
//
//   D2  <- panel TX      (pin 4, input -- unused here, listener.ino reads it)
//   D3  -> panel RX      (pin 3, output)    : LA CH0 "Fuzzer"
//   --     panel TX                         : LA CH1 "Board"
//   D7  PIN_MARKER      -> nothing          : LA CH2 "Marker"
//   D8  PIN_RESET       -> panel reset      : LA CH3 "Reset"  (LOW = stopped)
//   GND <-> panel GND    (pin 2) REQUIRED
//
// Reset wants a 15-30k pull-up in normal use. OMIT IT HERE: with the resistor
// in place the Arduino cannot assert reset cleanly and the board never comes
// up properly.
//
// The panel link is bit-banged on D3 rather than using the hardware UART on
// D0/D1, which is shared with the USB bridge -- see listener.ino. This sketch
// must emit exactly the bytes in STEPS[] and nothing else, so the bridge
// cannot be allowed anywhere near the panel.
//
// Marker channel:
//   20 ms pulse = reset just released (start of a trial)
//    1 ms pulse = immediately before each step's byte goes out
//
// Capture at >= 500 kHz.

#include <Arduino.h>
#include <util/atomic.h>

// ---------------------------------------------------------------- config ---

// What to send, as a list of (wait, byte) steps. The wait happens BEFORE the
// byte, timed from the previous step -- or from reset release for step 0.
//
// Behaviour of the first byte, sent while the panel broadcasts 0F 02 11:
//   0x14  ignored -- the announcement just continues
//   0x15  announcement stops, panel enters normal operation        <-- works
//   0x16  announcement stops, then after 258 ms the panel starts
//         broadcasting 18 03 80 9B every 53.6 ms and ignores buttons
//
// That 18 03 80 9B broadcast ("state B") is structurally identical to the boot
// announcement -- a message repeating forever while input is ignored -- so it
// is very likely waiting for a reply of its own. To hunt for it, use two
// steps: 0x16 to enter the state, then a candidate once the 258 ms transition
// has finished.
//
//   { {500, 0x16}, {500, 0x00} }
//
// Bytes in consecutive steps with wait 0 go out back-to-back, so a step can
// also carry a whole frame:  { {500, 0x0F}, {0, 0x02}, {0, 0x11} }
static const struct { uint16_t wait_ms; uint8_t byte; } STEPS[] = {
  { 500, 0x15 },
};

#define OBSERVE_MS            60000  // after the last step -> next trial
#define RESET_HOLD_MS         500    // how long the board is held stopped

#define PANEL_BAUD    9600UL

#define PIN_RX        2      // from panel TX -- not read here, kept as input
#define PIN_TX        3      // to panel RX
#define PIN_MARKER    7
#define PIN_RESET     8      // active low

// -------------------------------------------------------- software uart ----
// Bit-banged 8E1 transmitter on D3. Identical timing to listener.ino.
//
// 9600 baud = 104.1667 us/bit. BIT_US is the nominal value; BIT_ADJ_TX is the
// measured loop overhead subtracted from each bit delay. If the panel starts
// rejecting bytes, nudge BIT_US by a microsecond.

#define BIT_US        104
#define BIT_ADJ_TX    4

#define TX_SET(v)     do { if (v) PORTD |= _BV(PIN_TX); else PORTD &= ~_BV(PIN_TX); } while (0)

// Interrupts off: a stray ISR mid-frame stretches a bit and corrupts it. The
// call is synchronous, so on return the stop bit has already been sent -- no
// flush is needed and reset can never be yanked mid-byte.
static void panel_write_byte(uint8_t v) {
  uint8_t ones = 0;
  for (uint8_t i = 0; i < 8; i++) if (v & (1 << i)) ones++;
  uint8_t p = (ones & 1);                  // even parity

  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    TX_SET(0);                             // start bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    for (uint8_t i = 0; i < 8; i++) {      // LSB first
      TX_SET(v & (1 << i));
      delayMicroseconds(BIT_US - BIT_ADJ_TX);
    }
    TX_SET(p);
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    TX_SET(1);                             // stop bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
  }
}

// ------------------------------------------------------------------ misc ---

static void marker(uint16_t ms) {
  digitalWrite(PIN_MARKER, HIGH);
  delay(ms);
  digitalWrite(PIN_MARKER, LOW);
}

// ------------------------------------------------------------------ main ---

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_RX, INPUT_PULLUP);    // panel TX: unused here, never driven
  pinMode(PIN_TX, OUTPUT);
  digitalWrite(PIN_TX, HIGH);       // idle high
  pinMode(PIN_MARKER, OUTPUT);
  pinMode(PIN_RESET, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  digitalWrite(PIN_MARKER, LOW);
  digitalWrite(PIN_RESET, LOW);     // board stopped before anything is driven
}

void loop() {
  // 1. Cold start.
  digitalWrite(PIN_RESET, LOW);
  delay(RESET_HOLD_MS);
  digitalWrite(PIN_RESET, HIGH);
  marker(20);

  // 2. Walk the steps. One marker pulse per step, so the capture shows
  //    exactly which byte went out when.
  digitalWrite(LED_BUILTIN, HIGH);
  for (uint8_t i = 0; i < sizeof(STEPS) / sizeof(STEPS[0]); i++) {
    if (STEPS[i].wait_ms) delay(STEPS[i].wait_ms);
    marker(1);
    panel_write_byte(STEPS[i].byte);
  }
  digitalWrite(LED_BUILTIN, LOW);

  // 3. Watch what happens.
  delay(OBSERVE_MS);
}
