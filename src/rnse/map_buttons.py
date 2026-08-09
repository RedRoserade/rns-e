#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 André Carvalho
# SPDX-License-Identifier: Apache-2.0
"""
Guided key/rotary mapping for the RNS-E front panel.

Reads the output of listener/listener.ino over USB, walks you through pressing
each control, and records which bitmap bit (or rotary channel) each one drives.

    pip install pyserial
    ./map_buttons.py --port /dev/ttyACM0

Results are written to keymap.json after every control, so an interrupted
session is not lost. Re-running skips anything already mapped unless you pass
--redo.

Edit CONTROLS and ROTARIES below to match your panel.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import Counter

# --------------------------------------------------------------------------
# EDIT ME: the controls to map, in the order you want to be prompted for them.
# --------------------------------------------------------------------------

CONTROLS = [
    "fwd",
    "back",
    "top_left_quad",
    "top_right_quad",
    "bottom_left_quad",
    "bottom_right_quad",
    "return",
    "radio",
    "cd_tv_sd_media",
    "name",
    "tel",
    "nav",
    "info",
    "car",
    "setup",
    "flip_screen",
    "scroll_click",
    "eject",
]

# Rotary controls. The panel reports these on ADDR 0x0D as relative deltas.
ROTARIES = [
    "volume_knob",
    "scroll_wheel",
]

PRESSES_WANTED = 3          # how many presses to ask for per button
OUTFILE = "keymap.json"

KEY_ADDR = 0x0C
ENC_ADDR = 0x0D

MSG_RE = re.compile(r"^MSG\s+(\d+)\s+((?:[0-9A-Fa-f]{2}\s*)+?)\s+LEN=(\S+)\s+CK=(\S+)\s+PAR=(\S+)")


# ------------------------------------------------------------------ plumbing --

class Listener(threading.Thread):
    """Reads the Arduino, parses MSG lines, and accumulates key/rotary events."""

    daemon = True

    def __init__(self, ser, verbose=False):
        super().__init__()
        self.ser = ser
        self.verbose = verbose
        self.lock = threading.Lock()
        self.key_states = []        # [(t_ms, (P0..P5))]
        self.enc_events = []        # [(t_ms, (d0..d3))]
        self.bad = 0
        self.running = True

    def run(self):
        while self.running:
            try:
                raw = self.ser.readline()
            except Exception:
                break
            if not raw:
                continue
            line = raw.decode("ascii", "replace").strip()
            if self.verbose and line:
                print("   | " + line, file=sys.stderr)
            m = MSG_RE.match(line)
            if not m:
                continue
            t = int(m.group(1))
            data = [int(x, 16) for x in m.group(2).split()]
            if m.group(3) != "ok" or m.group(4) != "ok" or m.group(5) != "ok":
                with self.lock:
                    self.bad += 1
                continue
            payload = tuple(data[2:-1])
            with self.lock:
                if data[0] == KEY_ADDR:
                    self.key_states.append((t, payload))
                elif data[0] == ENC_ADDR:
                    self.enc_events.append((t, payload))

    def clear(self):
        with self.lock:
            self.key_states.clear()
            self.enc_events.clear()

    def snapshot(self):
        with self.lock:
            return list(self.key_states), list(self.enc_events)


def bits_of(payload):
    return {(i, b) for i, v in enumerate(payload) for b in range(8) if v >> b & 1}


def presses_from(states):
    """Collapse repeats and return the set of bits newly set at each change."""
    dedup = []
    for _, p in states:
        if not dedup or p != dedup[-1]:
            dedup.append(p)
    out, prev = [], set()
    for p in dedup:
        now = bits_of(p)
        new = now - prev
        if new:
            out.append(frozenset(new))
        prev = now
    return out


# -------------------------------------------------------------------- prompts --

def ask(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit("aborted")


def map_button(lis, name):
    """Returns dict or None (skipped)."""
    while True:
        lis.clear()
        ask("\n  >> press '%s' %d times, then hit Enter (s=skip): "
            % (name, PRESSES_WANTED))
        states, _ = lis.snapshot()
        if not states:
            print("     nothing received. Is the panel powered and wired?")
            if ask("     retry? [Y/n/s] ").strip().lower() in ("n", "s"):
                return None
            continue

        seen = presses_from(states)
        if not seen:
            print("     saw traffic but no press edge. Try again.")
            continue

        counts = Counter(seen)
        best, n = counts.most_common(1)[0]

        if len(best) > 1:
            print("     %d bits changed together: %s"
                  % (len(best), ", ".join("P%d.%d" % b for b in sorted(best))))
            print("     press ONE control at a time.")
            continue
        if len(counts) > 1:
            print("     inconsistent: %s"
                  % "; ".join("%s x%d" % (",".join("P%d.%d" % b for b in sorted(k)), c)
                              for k, c in counts.most_common()))
            print("     using the most frequent. Redo if that looks wrong.")

        byte_i, bit_i = next(iter(best))
        print("     -> P%d.%d  (payload byte %d, mask 0x%02X, %d press%s)"
              % (byte_i, bit_i, byte_i, 1 << bit_i, n, "" if n == 1 else "es"))
        r = ask("     accept? [Y/n/s] ").strip().lower()
        if r in ("", "y"):
            return {"byte": byte_i, "bit": bit_i, "mask": 1 << bit_i,
                    "label": "P%d.%d" % (byte_i, bit_i), "presses": n}
        if r == "s":
            return None


def map_rotary(lis, name):
    result = {}
    for direction, word in (("cw", "CLOCKWISE / up"), ("ccw", "COUNTER-CLOCKWISE / down")):
        while True:
            lis.clear()
            ask("\n  >> turn '%s' several detents %s, then hit Enter (s=skip): "
                % (name, word))
            _, encs = lis.snapshot()
            if not encs:
                print("     no rotary messages received.")
                if ask("     retry? [Y/n/s] ").strip().lower() in ("n", "s"):
                    return None
                continue

            chans, dirbits, detents = Counter(), Counter(), 0
            for _, pay in encs:
                for i, v in enumerate(pay):
                    if v:
                        chans[i] += 1
                        dirbits[(v >> 7) & 1] += 1
                        detents += v & 0x7F
            if not chans:
                print("     rotary messages were all zero. Try again.")
                continue
            if len(chans) > 1:
                print("     more than one channel moved: %s -- turn one at a time."
                      % ", ".join("ch%d" % c for c in chans))
                continue

            ch = next(iter(chans))
            db = dirbits.most_common(1)[0][0]
            print("     -> channel %d, direction bit %d, ~%d detents"
                  % (ch, db, detents))
            r = ask("     accept? [Y/n/s] ").strip().lower()
            if r in ("", "y"):
                result[direction] = {"channel": ch, "dir_bit": db, "detents": detents}
                break
            if r == "s":
                return None

    if len(result) == 2:
        a, b = result["cw"], result["ccw"]
        if a["channel"] != b["channel"]:
            print("     !! cw and ccw landed on different channels (%d vs %d)"
                  % (a["channel"], b["channel"]))
        if a["dir_bit"] == b["dir_bit"]:
            print("     !! cw and ccw produced the same direction bit (%d) --"
                  % a["dir_bit"])
            print("        the direction encoding may not be bit 7.")
    return result


# ----------------------------------------------------------------------- main --

def save(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


def write_markdown(path, data):
    lines = ["# RNS-E key map", "", "## Buttons", "",
             "| control | bit | payload byte | mask |", "|---|---|---|---|"]
    for name, v in sorted(data.get("buttons", {}).items(),
                          key=lambda kv: (kv[1]["byte"], kv[1]["bit"])):
        lines.append("| %s | %s | %d | 0x%02X |" % (name, v["label"], v["byte"], v["mask"]))
    lines += ["", "## Rotaries", "", "| control | channel | cw bit7 | ccw bit7 |",
              "|---|---|---|---|"]
    for name, v in sorted(data.get("rotaries", {}).items()):
        if "cw" in v and "ccw" in v:
            lines.append("| %s | %d | %d | %d |"
                         % (name, v["cw"]["channel"], v["cw"]["dir_bit"], v["ccw"]["dir_bit"]))
    # Generated file, so the licence has to be re-emitted every run or it is
    # lost the first time anyone re-maps a panel.
    lines += ["", "---", "",
              "Generated by `map_buttons.py` from the "
              "[rnse project](https://github.com/RedRoserade/rns-e). "
              "Licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)."]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port, e.g. /dev/ttyACM0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default=OUTFILE)
    ap.add_argument("--redo", action="store_true", help="remap already-mapped controls")
    ap.add_argument("--verbose", action="store_true", help="echo raw serial lines")
    args = ap.parse_args()

    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        raise SystemExit("pyserial is required:  pip install pyserial")

    port = args.port
    if not port:
        ports = list(list_ports.comports())
        if not ports:
            raise SystemExit("no serial ports found; pass --port")
        if len(ports) > 1:
            print("available ports:")
            for p in ports:
                print("  %s  %s" % (p.device, p.description))
            raise SystemExit("several ports found; pass --port")
        port = ports[0].device
        print("using %s" % port)

    data = {"buttons": {}, "rotaries": {}}
    if os.path.exists(args.out) and not args.redo:
        with open(args.out) as fh:
            data.update(json.load(fh))
        done = len(data["buttons"]) + len(data["rotaries"])
        if done:
            print("loaded %d existing mapping(s) from %s" % (done, args.out))

    ser = serial.Serial(port, args.baud, timeout=0.5)
    time.sleep(2.0)                    # Arduino resets when the port opens
    ser.reset_input_buffer()

    lis = Listener(ser, args.verbose)
    lis.start()

    print("\nPress each control ONE AT A TIME when prompted.")
    print("The panel only transmits on change, so silence between presses is normal.")

    try:
        for name in CONTROLS:
            if name in data["buttons"] and not args.redo:
                v = data["buttons"][name]
                print("\n  -- %s already mapped (%s), skipping" % (name, v["label"]))
                continue
            r = map_button(lis, name)
            if r:
                data["buttons"][name] = r
                save(args.out, data)

        for name in ROTARIES:
            if name in data["rotaries"] and not args.redo:
                print("\n  -- %s already mapped, skipping" % name)
                continue
            r = map_rotary(lis, name)
            if r:
                data["rotaries"][name] = r
                save(args.out, data)
    finally:
        lis.running = False
        try:
            ser.close()
        except Exception:
            pass

    save(args.out, data)
    md = os.path.splitext(args.out)[0] + ".md"
    write_markdown(md, data)

    print("\nwrote %s and %s" % (args.out, md))
    print("  %d buttons, %d rotaries" % (len(data["buttons"]), len(data["rotaries"])))

    # flag collisions -- two controls on the same bit means a misread
    seen = {}
    for name, v in data["buttons"].items():
        seen.setdefault(v["label"], []).append(name)
    for label, names in sorted(seen.items()):
        if len(names) > 1:
            print("  !! %s claimed by: %s" % (label, ", ".join(names)))

    if lis.bad:
        print("  note: %d malformed messages were discarded" % lis.bad)


if __name__ == "__main__":
    sys.exit(main())
