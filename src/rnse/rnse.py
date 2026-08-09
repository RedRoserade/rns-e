#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 André Carvalho
# SPDX-License-Identifier: Apache-2.0
"""
Decode RNS-E front-panel traffic from a sigrok .sr capture.

The panel speaks 9600 8E1 (8 data bits, EVEN parity, 1 stop). Messages are:

    [ADDR] [LEN] [payload x (LEN-2)] [CKSUM]
    total length = LEN + 1
    CKSUM = sum(all preceding bytes) & 0xFF

ADDR 0x0C is the key-state report: a 6-byte bitmap of every button, sent on
each change (press AND release), repeated 4x at ~59 ms, then silence.

No third-party dependencies -- stdlib only.

Usage:
    ./rnse.py capture.sr                    # full decode + key mapping
    ./rnse.py capture.sr --from 15          # skip the first 15 s
    ./rnse.py capture.sr --from 15 --to 40
    ./rnse.py capture.sr --channel Board    # decode a different channel
    ./rnse.py capture.sr --frames           # list every UART frame, not messages
    ./rnse.py capture.sr --baud 9600

Capture at >= 500 kHz. At 9600 baud a 20 kHz capture is only 2 samples/bit
and silently corrupts data bits 5..7.
"""

import argparse
import sys
import zipfile
from collections import OrderedDict

KEY_ADDR = 0x0C           # key-state report: 6-byte bitmap, absolute
ENC_ADDR = 0x0D           # rotary delta: 4 bytes, bit7=direction, bits0-6=detents
MSG_GAP_S = 0.005         # silence that separates two messages

ADDR_NAMES = {
    0x0C: "keys",
    0x0D: "rotary",
    0x0F: "announce?",
    0x18: "status",
}


# ---------------------------------------------------------------- .sr file ---

def load_sr(path):
    """Return (samples_as_bytes, samplerate_hz, {channel_name: bit_index})."""
    z = zipfile.ZipFile(path)
    meta = z.read("metadata").decode()

    rate, probes = None, OrderedDict()
    for line in meta.splitlines():
        line = line.strip()
        if line.startswith("samplerate"):
            v = line.split("=", 1)[1].strip()
            mult = 1
            for suf, m in (("GHz", 10**9), ("MHz", 10**6), ("kHz", 10**3), ("Hz", 1)):
                if v.endswith(suf):
                    v, mult = v[: -len(suf)].strip(), m
                    break
            rate = int(float(v) * mult)
        elif line.startswith("probe"):
            k, name = line.split("=", 1)
            probes[name.strip()] = int(k[len("probe"):]) - 1

    names = sorted((n for n in z.namelist() if n.startswith("logic-1-")),
                   key=lambda s: int(s.rsplit("-", 1)[1]))
    data = b"".join(z.read(n) for n in names)
    if rate is None:
        raise SystemExit("no samplerate in metadata")
    return data, rate, probes


def channel(data, bit):
    """Extract one channel as a bytes() of 0x00/0x01, at C speed."""
    return data.translate(bytes(((i >> bit) & 1) for i in range(256)))


def falling_edges(sig):
    """Indices where the signal goes 1 -> 0. Sparse, so find() is fast."""
    out, pos = [], 0
    while True:
        # a falling edge is a 0 that follows a 1
        i = sig.find(b"\x00", pos)
        if i < 0:
            break
        if i > 0 and sig[i - 1] == 1:
            out.append(i)
        j = sig.find(b"\x01", i)
        if j < 0:
            break
        pos = j
    return out


# ------------------------------------------------------------------ decode ---

def decode_uart(sig, samplerate, baud=9600, parity="even", ndata=8):
    """Sample mid-bit. Returns [(sample, value, parity_ok, framing_ok), ...]."""
    bit = samplerate / float(baud)
    n = len(sig)
    frames, edges, k = [], falling_edges(sig), 0
    while k < len(edges):
        st = edges[k]
        if sig[min(int(st + bit * 0.5), n - 1)] != 0:   # not a real start bit
            k += 1
            continue
        val = 0
        for b in range(ndata):
            p = int(st + bit * (1.5 + b))
            if p < n:
                val |= sig[p] << b
        idx, pbit = ndata, None
        if parity:
            p = int(st + bit * (1.5 + idx))
            if p < n:
                pbit, idx = sig[p], idx + 1
        p = int(st + bit * (1.5 + idx))
        stop = sig[p] if p < n else 1

        pok = None
        if pbit is not None:
            ones = bin(val).count("1") + pbit
            pok = (ones % 2 == 0) if parity == "even" else (ones % 2 == 1)
        frames.append((st, val, pok, stop == 1))

        end = st + bit * (idx + 1.5)
        while k < len(edges) and edges[k] < end:
            k += 1
    return frames


def split_by_len(group):
    """Subdivide a run of back-to-back frames using the LEN field.

    Two messages sent with no gap between them would otherwise be merged, so
    trust LEN when it produces a valid checksum and fall back to the whole run.
    """
    out, i = [], 0
    while i < len(group):
        if i + 1 >= len(group):
            out.append(group[i:])
            break
        n = group[i + 1][1] + 1                    # total length = LEN + 1
        cand = group[i:i + n]
        mb = tuple(f[1] for f in cand)
        if len(cand) == n and n >= 3 and (sum(mb[:-1]) & 0xFF) == mb[-1]:
            out.append(cand)
            i += n
        else:                                      # unparseable: emit the rest
            out.append(group[i:])
            break
    return out


def group_messages(frames, samplerate, gap_s=MSG_GAP_S):
    """Split the frame stream into messages on silence, then refine with LEN."""
    if not frames:
        return []
    gap, groups, cur = gap_s * samplerate, [], [frames[0]]
    for prev, curf in zip(frames, frames[1:]):
        if curf[0] - prev[0] > gap:
            groups.append(cur)
            cur = []
        cur.append(curf)
    groups.append(cur)
    return [m for g in groups for m in split_by_len(g)]


def check(msg_bytes):
    """(len_ok, cksum_ok) for one message."""
    if len(msg_bytes) < 3:
        return False, False
    len_ok = (msg_bytes[1] + 1) == len(msg_bytes)
    ck_ok = (sum(msg_bytes[:-1]) & 0xFF) == msg_bytes[-1]
    return len_ok, ck_ok


# -------------------------------------------------------------- key bitmap ---

def bitname(byte_i, bit_i):
    """Stable name for one key bit: P<payload byte>.<bit>."""
    return "P%d.%d" % (byte_i, bit_i)


def bits_set(payload):
    return {bitname(i, b) for i, v in enumerate(payload) for b in range(8) if v >> b & 1}


def analyse_keys(events):
    """events = [(t, payload_tuple)] deduped. Returns press/release transitions."""
    trans, prev = [], set()
    for t, payload in events:
        now = bits_set(payload)
        pressed, released = sorted(now - prev), sorted(prev - now)
        if pressed or released:
            trans.append((t, pressed, released, payload))
        prev = now
    return trans


# -------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--channel", default="Board", help="channel to decode (default: Board)")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--parity", default="even", choices=["even", "odd", "none"])
    ap.add_argument("--from", dest="t0", type=float, default=0.0, metavar="SEC")
    ap.add_argument("--to", dest="t1", type=float, default=None, metavar="SEC")
    ap.add_argument("--frames", action="store_true", help="list raw frames, not messages")
    ap.add_argument("--all-channels", action="store_true", help="summarise every channel")
    args = ap.parse_args()

    data, rate, probes = load_sr(args.file)
    dur = len(data) / float(rate)
    print("%s: %d samples @ %d Hz = %.3f s" % (args.file, len(data), rate, dur))
    print("channels: %s\n" % ", ".join("%s=D%d" % (n, b) for n, b in probes.items()))

    if args.all_channels:
        for name, bitidx in probes.items():
            sig = channel(data, bitidx)
            e = falling_edges(sig)
            print("  %-8s high=%.4f  falling-edges=%d" % (name, sum(sig) / len(sig), len(e)))
        print()

    if args.channel not in probes:
        raise SystemExit("no channel %r; have %s" % (args.channel, list(probes)))
    sig = channel(data, probes[args.channel])

    frames = decode_uart(sig, rate, args.baud,
                         None if args.parity == "none" else args.parity)
    lo = args.t0 * rate
    hi = (args.t1 if args.t1 is not None else dur) * rate
    frames = [f for f in frames if lo <= f[0] <= hi]

    perr = sum(1 for f in frames if f[2] is False)
    ferr = sum(1 for f in frames if not f[3])
    print("channel %s: %d frames, %d parity errors, %d framing errors"
          % (args.channel, len(frames), perr, ferr))
    if perr or ferr:
        print("  !! errors mean wrong baud/format, or too low a sample rate")
    if not frames:
        return

    if args.frames:
        for st, v, pok, fok in frames:
            print("  %9.6f  %02X  %s%s" % (st / rate, v,
                  "" if pok else " PARITY", "" if fok else " FRAMING"))
        return

    msgs = group_messages(frames, rate)
    print("messages: %d\n" % len(msgs))

    events, enc_events, prev_t = [], [], None
    print("   t(s)      gap(ms)  message                          len cks")
    for m in msgs:
        t, mb = m[0][0], tuple(f[1] for f in m)
        len_ok, ck_ok = check(mb)
        gap = "      -" if prev_t is None else "%7.1f" % ((t - prev_t) / rate * 1000)
        print("  %8.3f  %s  %-32s %s %s"
              % (t / rate, gap, " ".join("%02X" % x for x in mb),
                 "ok " if len_ok else "BAD", "ok " if ck_ok else "BAD"))
        prev_t = t
        if ck_ok:
            if mb[0] == KEY_ADDR:
                events.append((t / rate, mb[2:-1]))
            elif mb[0] == ENC_ADDR:
                enc_events.append((t / rate, mb[2:-1]))

    bad = sum(1 for m in msgs if not all(check(tuple(f[1] for f in m))))
    print("\n%d/%d messages structurally valid" % (len(msgs) - bad, len(msgs)))

    addrs = {}
    for m in msgs:
        mb = tuple(f[1] for f in m)
        if check(mb)[1]:
            addrs[mb[0]] = addrs.get(mb[0], 0) + 1
    print("\naddresses seen: " + ", ".join(
        "%02X (%s) x%d" % (a, ADDR_NAMES.get(a, "?"), c) for a, c in sorted(addrs.items())))

    if enc_events:
        # 4x repeats of an identical delta are retransmits of ONE event, not
        # four movements: collapse bursts that repeat within ~250 ms.
        bursts = [enc_events[0]]
        for t, p in enc_events[1:]:
            lt, lp = bursts[-1]
            if not (p == lp and t - lt < 0.25):
                bursts.append((t, p))
            else:
                bursts[-1] = (lt, lp)
        print("\n=== rotary (ADDR %02X) ===" % ENC_ADDR)
        pos = {}
        for t, pay in bursts:
            for i, v in enumerate(pay):
                if not v:
                    continue
                step = v & 0x7F
                delta = -step if v & 0x80 else step
                pos[i] = pos.get(i, 0) + delta
                print("  %8.3f  [%s]  ch%d %+d detent%s  (cumulative %+d)"
                      % (t, " ".join("%02X" % x for x in pay), i, delta,
                         "" if step == 1 else "s", pos[i]))
        print("\n  %d rotary channel(s) active: %s" % (len(pos),
              ", ".join("ch%d net %+d" % (k, v) for k, v in sorted(pos.items()))))

    if not events:
        return

    # collapse the 4x repeats into one entry per distinct consecutive state
    dedup = [events[0]]
    for t, p in events[1:]:
        if p != dedup[-1][1]:
            dedup.append((t, p))

    print("\n=== key bitmap (ADDR %02X) ===" % KEY_ADDR)
    trans = analyse_keys(dedup)
    for t, pressed, released, payload in trans:
        pay = " ".join("%02X" % x for x in payload)
        act = []
        if pressed:
            act.append("PRESS   " + ",".join(pressed))
        if released:
            act.append("RELEASE " + ",".join(released))
        print("  %8.3f  [%s]  %s" % (t, pay, "   ".join(act)))

    seen = OrderedDict()
    for _, pressed, _, _ in trans:
        for b in pressed:
            seen[b] = seen.get(b, 0) + 1
    print("\n=== distinct keys seen: %d ===" % len(seen))
    for b, c in seen.items():
        i, bi = (int(x) for x in b[1:].split("."))
        print("  %-6s payload byte %d bit %d (mask 0x%02X)  pressed %dx"
              % (b, i, bi, 1 << bi, c))


if __name__ == "__main__":
    sys.exit(main())
