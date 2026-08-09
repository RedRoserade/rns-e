// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
//
// RNS-E front panel fuzzer  (MB90561A control board)
//
// ---------------------------------------------------------------------------
// Wiring -- identical to listener.ino, so one harness serves both sketches
// ---------------------------------------------------------------------------
// The panel connector is a 9-pin Molex PicoBlade, 1.25 mm pitch:
//   1 VCC(+5V)  2 GND  3 RX  4 TX  5 PPG1  6 reset  7 power btn  8,9 backlight
//
//   D2  <- panel TX      (pin 4, input -- unused here, listener.ino reads it)
//   D3  -> panel RX      (pin 3, output)    : LA CH0 "Fuzzer"
//   --     panel TX                         : LA CH1 "Board"
//   D7  PIN_MARKER      -> nothing          : LA CH2 "Marker"
//   D8  PIN_RESET       -> panel reset      : LA CH3 "Reset"  (LOW = stopped)
//   GND <-> panel GND    (pin 2) REQUIRED, common to Arduino + LA + panel
//
// Reset wants a 15-30k pull-up in normal use. OMIT IT HERE: with the resistor
// in place the Arduino cannot assert reset cleanly and the board never comes
// up properly.
//
// The panel link is bit-banged on D2/D3 rather than using the hardware UART on
// D0/D1. Same reason as listener.ino -- D0/D1 are shared with the USB bridge,
// so anything the bridge emits (notably during a sketch upload) would land on
// the panel as input. For a fuzzer that is disqualifying: the whole point is
// knowing exactly which bytes went out and when.
//
// SoftwareSerial cannot be used: it is 8N1 only, and the panel needs 8E1.
//
// Sample the analyzer at >= 500 kHz (1 MHz preferred). At 9600 baud a 20 kHz
// capture is only 2.08 samples/bit, which silently corrupts data bits 5..7.

#include <Arduino.h>
#include <util/atomic.h>

// ---------------------------------------------------------------- config ---

// Frame format. Evidence from the board's own traffic says 8E1: all observed
// board bytes satisfy even parity, and messages carry an additive checksum
// (0F+02=11, 18+03+40=5B). Set to 0 to go back to raw 9-bit for comparison.
#define USE_8E1        1

#define PANEL_BAUD     9600UL

#define PIN_RX         2      // from panel TX -- not read here, kept as input
#define PIN_TX         3      // to panel RX
#define PIN_MARKER     7
#define PIN_RESET      8      // active low

#define RESET_HOLD_MS  1000   // how long to hold the board stopped
#define BOOT_MS        15000  // let the board boot; captures baseline heartbeat
// The board goes deaf for ~200 ms after replying (it retries 2-3 times at
// ~53 ms waiting for an ack, then re-arms). At 150 ms it answered only every
// SECOND byte, so half the sweep was never tested. Must exceed the observed
// 306 ms re-arm interval.
#define BYTE_GAP_MS    400
#define SWEEP_PAUSE_MS 500   // quiet time after the sweep, before reset

#define FUZZ_START     0x00
#define FUZZ_END       0xFF

#define DO_FUZZ 1

// -------------------------------------------------------- software uart ----
// Bit-banged 8E1 transmitter on D3. Identical timing to listener.ino.
//
// 9600 baud = 104.1667 us/bit. BIT_US is the nominal value; BIT_ADJ_TX is the
// measured loop overhead subtracted from each bit delay. If the panel starts
// rejecting bytes, nudge BIT_US by a microsecond.

#define BIT_US        104
#define BIT_ADJ_TX    4

#define TX_SET(v)     do { if (v) PORTD |= _BV(PIN_TX); else PORTD &= ~_BV(PIN_TX); } while (0)

// Transmit one frame. The 9th bit is parity under 8E1, or a forced 1 in 9-bit
// mode -- same wire position either way, which is exactly why the two framings
// were confusable in the first place.
//
// Interrupts off: a stray ISR mid-frame stretches a bit and corrupts it. The
// call is synchronous, so on return the stop bit has already been sent -- no
// flush is needed and reset can never be yanked mid-byte.
static void panel_write_byte(uint8_t v) {
#if USE_8E1
  uint8_t ones = 0;
  for (uint8_t i = 0; i < 8; i++) if (v & (1 << i)) ones++;
  uint8_t ninth = (ones & 1);              // even parity
#else
  uint8_t ninth = 1;                       // 9th data bit, forced high
#endif

  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    TX_SET(0);                             // start bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    for (uint8_t i = 0; i < 8; i++) {      // LSB first
      TX_SET(v & (1 << i));
      delayMicroseconds(BIT_US - BIT_ADJ_TX);
    }
    TX_SET(ninth);
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
    TX_SET(1);                             // stop bit
    delayMicroseconds(BIT_US - BIT_ADJ_TX);
  }
}

// ---------------------------------------------------------------- marker ---
// Pulses on an otherwise-unused pin so the capture can be segmented without
// guessing: 20 ms = sweep start, 1 ms = one pulse immediately before each byte.
// Counting short pulses after a long one gives the exact byte index.

static void marker(uint16_t ms) {
  digitalWrite(PIN_MARKER, HIGH);
  delay(ms);
  digitalWrite(PIN_MARKER, LOW);
}

// ------------------------------------------------------------------ main ---

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_RX, INPUT_PULLUP);         // panel TX: unused here, never driven
  pinMode(PIN_TX, OUTPUT);
  digitalWrite(PIN_TX, HIGH);            // idle high
  pinMode(PIN_MARKER, OUTPUT);
  pinMode(PIN_RESET, OUTPUT);

  digitalWrite(LED_BUILTIN, LOW);
  digitalWrite(PIN_MARKER, LOW);

  // Board stopped from the very first instant, before anything is driven at it.
  digitalWrite(PIN_RESET, LOW);
}

void loop() {
  // 1. Board stopped.
  digitalWrite(PIN_RESET, LOW);
  delay(RESET_HOLD_MS);

  // 2. Release reset, let it boot. The baseline heartbeat recorded during this
  //    window is the reference for spotting any change the sweep causes.
  digitalWrite(PIN_RESET, HIGH);
  delay(BOOT_MS);

  // 3. Sweep.
  digitalWrite(LED_BUILTIN, HIGH);
  marker(20);

#if DO_FUZZ
  for (uint16_t b = FUZZ_START; b <= FUZZ_END; b++) {
    marker(1);
    panel_write_byte((uint8_t)b);
    delay(BYTE_GAP_MS);
  }

  digitalWrite(LED_BUILTIN, LOW);
#endif

  // 4. Quiet tail, so a late reply is attributable to the final byte and not
  //    confused with the reset that follows.
  delay(SWEEP_PAUSE_MS);
}
