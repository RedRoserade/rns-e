#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 André Carvalho
# SPDX-License-Identifier: Apache-2.0
"""
Guided CAN bench session for the RNS-E head unit (docs/CANBUS.md).

Tells you what to do at each step (power on, press a button, look at the
panel), does all the CAN work itself, and logs every frame in both directions
plus your answers to one file you can hand over for analysis.

    uv run src/rnse/can_session.py

You need no CAN knowledge to run it. Answer the questions; press Enter to go
on; Ctrl-C at any point stops all transmission and keeps the log.

Log format, one line per frame:

    (epoch_seconds) can0 RX|TX ID#DATA
    # step / answer / note lines start with '#'

RX is the head unit, TX is this host (this tool, or anything else on the
host transmitting on the same interface).
"""

import argparse
import os
import subprocess
import sys
import threading
import time

import can

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from can_backlight import (  # noqa: E402
    HEAD_UNIT_NM_ID,
    ILLUM_ID,
    IGNITION_ID,
    IGNITION_ON,
    IGNITION_PERIOD,
    NM_OPCODES,
    NmPeer,
    hexbytes,
)

ILLUM_PERIOD = 0.2

# 0x635 payloads tried in the backlight step, with what each one is testing.
# Ranges from the firmware (FIRMWARE.md §5.2.1): byte 0 is valid 0x06..0x7E,
# byte 1 (KL58s) 0x00..0x7E, both used up to 0x64; byte 2 is never read. An
# invalid byte is replaced by the last good value or 0x50, not treated as off.
ILLUM_TESTS = [
    ("06 00 00", "lowest valid levels (the baseline)"),
    ("64 64 00", "display and KL58s at the maximum, 0x64"),
    ("06 64 00", "KL58s alone at maximum: does it drive the button lights?"),
    ("64 00 00", "display alone at maximum"),
    ("00 FF 00", "both bytes invalid: expect a fallback, not 'lights on'"),
    ("06 00 00", "back to the lowest"),
]


class Recorder(can.Listener):
    """Writes every frame to the log and keeps a little state for the prompts."""

    def __init__(self, path):
        self.f = open(path, "w", buffering=1)
        self.lock = threading.Lock()
        self.ids = {}           # arbitration id -> count, head unit only
        self.new_ids = []       # ids the unit sent that we had not seen before
        self.nm_last = None
        self.nm_changes = []    # (time, payload) whenever 0x436 changes
        self.local_ids = set()

    def on_message_received(self, msg):
        if msg.is_error_frame:
            self.note(f"ERROR FRAME {msg}")
            return
        data = bytes(msg.data)
        with self.lock:
            self.f.write(f"({msg.timestamp:.6f}) can0 {'RX' if msg.is_rx else 'TX'} "
                         f"{msg.arbitration_id:03X}#{data.hex().upper()}\n")
            if not msg.is_rx:
                self.local_ids.add(msg.arbitration_id)
                return
            if msg.arbitration_id not in self.ids:
                self.new_ids.append((msg.timestamp, msg.arbitration_id, data))
            self.ids[msg.arbitration_id] = self.ids.get(msg.arbitration_id, 0) + 1
            if msg.arbitration_id == HEAD_UNIT_NM_ID and data != self.nm_last:
                self.nm_last = data
                self.nm_changes.append((msg.timestamp, data))

    def note(self, text):
        with self.lock:
            for line in str(text).splitlines() or [""]:
                self.f.write(f"# {time.time():.6f} {line}\n")

    def snapshot(self):
        with self.lock:
            return dict(self.ids), list(self.new_ids), list(self.nm_changes)


def nm_words(data):
    if data is None or len(data) < 2:
        return "nothing"
    kind = NM_OPCODES.get(data[1], f"opcode {data[1]:02X}")
    return f"{kind} → node {data[0]:02X}"


class Session:
    def __init__(self, channel, log_path):
        self.channel = channel
        self.log_path = log_path
        self.rec = Recorder(log_path)
        self.logbus = can.Bus(interface="socketcan", channel=channel)
        self.txbus = can.Bus(interface="socketcan", channel=channel)
        self.log_notifier = can.Notifier(self.logbus, [self.rec])
        self.tx_notifier = can.Notifier(self.txbus, [])
        self.nm = None
        self.ign = None
        self.illum = None
        self.answers = []

    # -- talking to the person ---------------------------------------------

    def say(self, text):
        print(text)
        self.rec.note(text)

    def step(self, n, title):
        bar = "─" * 60
        print(f"\n{bar}\n STEP {n}: {title}\n{bar}")
        self.rec.note(f"STEP {n}: {title}")

    def do(self, instruction):
        """An action for the person; waits for Enter."""
        self.rec.note(f"DO: {instruction}")
        input(f"\n  ▶ {instruction}\n    Press Enter when done. ")
        self.rec.note("DONE")

    def ask(self, question, choices=None):
        """A question; records the answer. With choices, only those are accepted;
        without, any text (or nothing) is."""
        hint = f" [{'/'.join(choices)}]" if choices else ""
        while True:
            a = input(f"\n  ? {question}{hint} ").strip()
            if not choices or a.lower() in choices:
                break
            print(f"    please answer one of: {', '.join(choices)}")
        self.rec.note(f"Q: {question}")
        self.rec.note(f"A: {a}")
        self.answers.append((question, a))
        return a.lower()

    def wait(self, seconds, what):
        self.rec.note(f"WAIT {seconds}s: {what}")
        end = time.time() + seconds
        while (left := end - time.time()) > 0:
            ids, _, nm = self.rec.snapshot()
            state = nm_words(nm[-1][1]) if nm else "silent"
            print(f"\r    {what}: {left:4.0f}s left   unit: {state:<28}", end="", flush=True)
            time.sleep(0.25)
        print()

    # -- the CAN side --------------------------------------------------------

    def start_nm(self):
        if self.nm is None:
            self.nm = NmPeer(self.txbus, 0x00)
            self.tx_notifier.add_listener(self.nm)
            self.nm.start()
            self.rec.note("TX: NM peer node 0x00 started")

    def start_ign(self):
        if self.ign is None:
            msg = can.Message(arbitration_id=IGNITION_ID, data=IGNITION_ON,
                              is_extended_id=False)
            self.ign = self.txbus.send_periodic(msg, IGNITION_PERIOD)
            self.rec.note(f"TX: 0x{IGNITION_ID:03X} {hexbytes(IGNITION_ON)} every 100 ms")

    def set_illum(self, payload):
        msg = can.Message(arbitration_id=ILLUM_ID, data=bytes.fromhex(payload),
                          is_extended_id=False)
        if self.illum is None:
            self.illum = self.txbus.send_periodic(msg, ILLUM_PERIOD)
        else:
            self.illum.modify_data(msg)
        self.rec.note(f"TX: 0x{ILLUM_ID:03X} {payload} every 200 ms")

    def stop_all(self):
        if self.illum is not None:
            self.illum.stop()
            self.illum = None
        if self.ign is not None:
            self.ign.stop()
            self.ign = None
        if self.nm is not None:
            self.tx_notifier.remove_listener(self.nm)
            self.nm.stop()
            self.nm = None
        self.rec.note("TX: everything stopped")

    def close(self):
        self.stop_all()
        self.tx_notifier.stop()
        self.log_notifier.stop()
        self.txbus.shutdown()
        self.logbus.shutdown()

    # -- reporting -----------------------------------------------------------

    def report_since(self, t0, label):
        ids, new, nm = self.rec.snapshot()
        new = [x for x in new if x[0] >= t0]
        nm = [x for x in nm if x[0] >= t0]
        lines = [f"  {label}:"]
        if nm:
            lines.append(f"    unit network state went through: "
                         + ", then ".join(nm_words(d) for _, d in nm[:6])
                         + (" …" if len(nm) > 6 else ""))
        else:
            lines.append("    unit network state: no change")
        for ts, arb, data in new:
            lines.append(f"    NEW message from the unit: 0x{arb:03X} {hexbytes(data)}"
                         f"  at +{ts - t0:.1f}s")
        if not new:
            lines.append("    no new message types from the unit")
        if self.nm:
            lines.append(f"    ring with the unit: {'UP' if self.nm.ring_up else 'DOWN'} "
                         f"({self.nm.stats['ring_rx']} rings so far)")
        self.say("\n".join(lines))


def preflight(channel):
    try:
        out = subprocess.run(["ip", "-details", "-statistics", "link", "show", channel],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        sys.exit(f"{channel} does not exist. Plug the CAN adapter in, then:\n"
                 f"  sudo ip link set {channel} up type can bitrate 100000")
    problems = []
    if "state UP" not in out and ",UP" not in out:
        problems.append(f"{channel} is down:  sudo ip link set {channel} up type can bitrate 100000")
    if "bitrate 100000 " not in out:
        problems.append(f"{channel} is not at 100 kbit/s:\n"
                        f"  sudo ip link set {channel} down\n"
                        f"  sudo ip link set {channel} up type can bitrate 100000")
    if "BUS-OFF" in out:
        problems.append(f"{channel} is bus-off. Check wiring, and that NO 120 Ω resistor is fitted.")
    if problems:
        sys.exit("\n".join(problems))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--channel", default="can0")
    ap.add_argument("--out", default=None,
                    help="log file (default captures/session-<time>.log)")
    args = ap.parse_args()

    link = preflight(args.channel)
    os.makedirs("captures", exist_ok=True)
    path = args.out or time.strftime("captures/session-%Y%m%d-%H%M%S.log")
    s = Session(args.channel, path)
    s.rec.note(f"rnse can_session on {args.channel}")
    s.rec.note(link)

    print(__doc__.split("\n\n")[0])
    print(f"Logging everything to {path}\n")
    print("Checklist before starting:")
    print("  • head unit wired: D15 +12 V, D12 ground, D9 CAN-H, D10 CAN-L")
    print("  • NO 120 Ω resistor across CAN-H / CAN-L (this bus breaks with one)")
    print("  • front panel connected, so you can see its button backlight")
    print("  • nothing else transmitting on the CAN adapter (listening is fine)")

    try:
        # 1 — a quiet bus with the unit off
        s.step(1, "unit OFF: check the bus is quiet")
        s.do("Switch the 12 V supply to the head unit OFF.")
        t = time.time()
        s.wait(3, "listening")
        _, new, _ = s.rec.snapshot()
        if [x for x in new if x[0] >= t]:
            s.say("  ⚠ Something is still transmitting with the unit off. Is the supply really off?")
        else:
            s.say("  ✓ bus quiet")

        # 2 — power-on, no button
        s.step(2, "power on, do NOT touch the power button")
        s.do("Switch the 12 V supply ON, then press Enter straight away. "
             "Do not press the power button yet.")
        t = time.time()
        s.wait(12, "recording power-up")
        s.report_since(t, "after power-on")
        s.ask("What does the screen show? (e.g. black, Audi logo, PIN, flickering)")
        s.ask("Are the front-panel button lights on?", ["y", "n"])

        # 3 — the button
        s.step(3, "press the power button")
        s.do("Press the power button on the front panel once.")
        t = time.time()
        s.wait(15, "recording")
        s.report_since(t, "after the power button")
        s.ask("What does the unit do now? (screen, sounds, reboots…)")
        s.ask("If it is boot-looping: roughly how many seconds per cycle? "
              "(Enter if not looping / not sure)")

        # 4 — become a second node, and turn the ignition on
        s.step(4, "give the unit a partner on the bus, and ignition on")
        s.say("  The tool now answers the unit's network handshake (it is otherwise\n"
              "  alone and gives up), and sends the 'ignition on' message.")
        t = time.time()
        s.start_nm()
        s.start_ign()
        s.wait(30, "partner + ignition running")
        s.report_since(t, "with a partner and ignition")
        s.ask("Did anything change on the unit in the last 30 s? (describe, or 'no')")
        s.ask("Are the front-panel button lights on?", ["y", "n"])

        # 5 — the backlight message
        s.step(5, "backlight commands")
        s.say("  Each test runs 8 s. Keep your eyes on the front-panel button lights.")
        for payload, meaning in ILLUM_TESTS:
            t = time.time()
            s.say(f"\n  sending 0x635 = {payload}: {meaning}")
            s.set_illum(payload)
            s.wait(8, f"0x635 {payload}")
            s.report_since(t, f"during 0x635 {payload}")
            s.ask("Button lights now? (on / off / dim / brighter / no change / …)")

        # 6 — let go, and watch what the unit does alone again
        s.step(6, "stop transmitting")
        t = time.time()
        s.stop_all()
        s.wait(8, "listening, nothing transmitted")
        s.report_since(t, "after we went quiet")
        s.ask("Anything else you noticed during the session?")

    except (KeyboardInterrupt, EOFError):
        print("\n  stopped early")
        s.rec.note("SESSION STOPPED EARLY")
    finally:
        s.close()
        ids, _, _ = s.rec.snapshot()
        summary = ", ".join(f"0x{k:03X}×{v}" for k, v in sorted(ids.items())) or "nothing"
        s.rec.note(f"SUMMARY: unit sent {summary}")
        print(f"\nAll transmission stopped. Unit sent: {summary}")
        print(f"Log: {path}  ← hand this over for analysis")


if __name__ == "__main__":
    main()
