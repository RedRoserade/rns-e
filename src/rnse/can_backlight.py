#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 André Carvalho
# SPDX-License-Identifier: Apache-2.0
"""
Interactive CAN console for the RNS-E illumination experiment (docs/CANBUS.md).

Transmits the third-party illumination frame 0x635 and, optionally, the
ignition keep-alive 0x271, and shows what the head unit says back.

    uv run src/rnse/can_backlight.py              # can0, 0x635 every 200 ms
    uv run src/rnse/can_backlight.py --channel can1 --period 100

The interface must already be up at 100 kbit/s:

    sudo ip link set can0 up type can bitrate 100000

Other programs (cangaroo, candump) can stay attached to the same interface;
SocketCAN delivers our transmitted frames to them too, so a capture running
alongside records exactly what was sent and when.

Everything about 0x635's payload is UNVERIFIED (CANBUS.md §3):

    [0]  display backlight   0x00 .. 0x64
    [1]  button backlight    0x00 .. 0x64
    [2]  unknown

Values up to 0xFF are allowed on purpose, since settling the range is one of
the things this tool is for. Type `help` at the prompt for commands.
"""

import argparse
import cmd
import shlex
import sys
import threading
import time

import can

# --------------------------------------------------------------------------
# Identifiers (CANBUS.md §3, §4 — third-party, unverified)
# --------------------------------------------------------------------------

ILLUM_ID = 0x635            # [display, button, unknown]
IGNITION_ID = 0x271         # terminal 15
IGNITION_ON = bytes([0x01, 0x80])
IGNITION_PERIOD = 0.100

LEVEL_MAX = 0x64            # stated top of range; 0xFF also seen in the wild

# The head unit's own frame, seen on every power-up (boot-up.asc): VAG OSEK
# network management. ID 0x420 + node, so the unit is node 0x16; byte 0 =
# logical successor node; byte 1 = opcode. Opcodes as measured on the bench
# (CANBUS.md §4.1) — note ring and alive are the other way round from the
# usual OSEK write-up:
#   02 alive: "I (re)started"   01 ring: token to byte 0   04 limp-home
# Alone, the unit sends alive/ring to itself five times, then limp-home every
# 500 ms. With a peer that answers correctly it rings that peer every 100 ms.
NM_BASE = 0x420
HEAD_UNIT_NM_ID = 0x436
HEAD_UNIT_NODE = HEAD_UNIT_NM_ID - NM_BASE
NM_RING, NM_ALIVE, NM_LIMP = 0x01, 0x02, 0x04
NM_TTYP = 0.050             # delay before passing the ring back (unit's own ring period is 100 ms)
NM_RING_LOST = 0.500        # no ring for this long: announce again
NM_OPCODES = {
    0x01: "ring",
    0x02: "alive",
    0x04: "limp-home",
}


def hexbytes(data):
    return " ".join(f"{b:02X}" for b in data)


def parse_byte(text):
    """Accepts 0..255 decimal, or 0x-prefixed / h-suffixed hex."""
    t = text.strip().lower()
    if t.startswith("0x"):
        v = int(t, 16)
    elif t.endswith("h"):
        v = int(t[:-1], 16)
    elif t.endswith("%"):
        v = round(float(t[:-1]) * LEVEL_MAX / 100)
    else:
        v = int(t, 10)
    if not 0 <= v <= 0xFF:
        raise ValueError(f"{text!r} is outside 0..255")
    return v


def describe_nm(data):
    if len(data) < 2:
        return ""
    op = NM_OPCODES.get(data[1], f"op 0x{data[1]:02X}")
    return f"NM → node 0x{data[0]:02X}, {op}"


class Monitor(can.Listener):
    """Prints received frames. 0x436 NM traffic is printed only when it changes,
    so the unit's 500 ms heartbeat does not bury everything else."""

    def __init__(self):
        self.enabled = True
        self.show_all = False
        self.last = {}
        self.counts = {}
        self.lock = threading.Lock()

    def on_message_received(self, msg):
        if msg.is_error_frame:
            if self.enabled:
                print(f"\r[rx] ERROR FRAME {msg}")
            return
        if not msg.is_rx:
            return      # sent by this host (our BCM tasks, cangaroo): not the unit
        data = bytes(msg.data)
        with self.lock:
            self.counts[msg.arbitration_id] = self.counts.get(msg.arbitration_id, 0) + 1
            changed = self.last.get(msg.arbitration_id) != data
            self.last[msg.arbitration_id] = data
        if not self.enabled or not (changed or self.show_all):
            return
        note = describe_nm(data) if msg.arbitration_id == HEAD_UNIT_NM_ID else ""
        stamp = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
        print(f"\r[rx {stamp}] 0x{msg.arbitration_id:03X} [{len(data)}] "
              f"{hexbytes(data):<24}{note}")


class NmPeer(can.Listener):
    """A second OSEK NM node, so the head unit is not alone on the bus.

    Worked out on the bench (CANBUS.md §4.1). The unit forgets its peers every
    time it restarts, so a single announcement is not enough:

    - the unit sends alive not naming us → it just restarted; announce at once,
      so its next ring names us;
    - the unit rings us → pass the ring back to it after NM_TTYP;
    - the unit is in limp-home, or the ring has gone quiet → announce again.

    Sleep flags are never set, so the network is always asked to stay awake.
    """

    def __init__(self, bus, node):
        self.bus = bus
        self.node = node
        self.stats = {"alive": 0, "ring": 0, "ring_rx": 0}
        self.seen = {}      # (successor, opcode) from the unit -> count
        self.unit_state = None
        self.last_ring_rx = 0.0
        self.last_alive_tx = 0.0
        self.announce_now = False
        self.ring_due = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._tick, daemon=True)

    @property
    def arb_id(self):
        return NM_BASE + self.node

    @property
    def ring_up(self):
        return time.monotonic() - self.last_ring_rx < 0.3

    def _send(self, successor, op, kind):
        self.bus.send(can.Message(arbitration_id=self.arb_id,
                                  data=bytes([successor, op, 0, 0, 0, 0]),
                                  is_extended_id=False))
        self.stats[kind] += 1

    def _announce(self):
        self._send(HEAD_UNIT_NODE, NM_ALIVE, "alive")
        self.last_alive_tx = time.monotonic()

    def start(self):
        self._announce()
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    def on_message_received(self, msg):
        if msg.arbitration_id != HEAD_UNIT_NM_ID or len(msg.data) < 2 \
                or not msg.is_rx:
            return
        successor, op = msg.data[0], msg.data[1]
        with self.lock:
            self.unit_state = op
            self.seen[(successor, op)] = self.seen.get((successor, op), 0) + 1
            if op == NM_RING and successor == self.node:
                self.stats["ring_rx"] += 1
                self.last_ring_rx = time.monotonic()
                self.ring_due = self.last_ring_rx + NM_TTYP
            elif op == NM_ALIVE and successor != self.node:
                self.announce_now = True

    def _tick(self):
        while not self.stop_event.wait(0.005):
            now = time.monotonic()
            with self.lock:
                ring = self.ring_due is not None and now >= self.ring_due
                if ring:
                    self.ring_due = None
                announce, self.announce_now = self.announce_now, False
                state, last_ring = self.unit_state, self.last_ring_rx
            try:
                if ring:
                    self._send(HEAD_UNIT_NODE, NM_RING, "ring")
                elif announce or (now - last_ring > NM_RING_LOST
                                  and now - self.last_alive_tx > NM_RING_LOST):
                    self._announce()
            except can.CanError as e:
                print(f"\r[nm] send failed: {e}")


class Console(cmd.Cmd):
    intro = ("RNS-E illumination console. 0x635 is NOT being sent yet.\n"
             "Try: nm on | ign on | on | off | level 50% | status | help\n")
    prompt = "rnse-can> "

    def __init__(self, bus, monitor, period):
        super().__init__()
        self.bus = bus
        self.monitor = monitor
        self.period = period
        self.payload = [0x00, 0x00, 0x00]
        self.on_level = [LEVEL_MAX, LEVEL_MAX]
        self.illum_task = None
        self.ign_task = None
        self.sweep_stop = threading.Event()
        self.sweep_thread = None
        self.nm = None

    # -- transmission ------------------------------------------------------

    def _illum_msg(self):
        return can.Message(arbitration_id=ILLUM_ID, data=bytes(self.payload),
                           is_extended_id=False)

    def _apply(self):
        """Push the current payload: update the periodic task, or start it."""
        msg = self._illum_msg()
        if self.illum_task is None:
            self.illum_task = self.bus.send_periodic(msg, self.period)
        else:
            self.illum_task.modify_data(msg)
        print(f"[tx] 0x{ILLUM_ID:03X} {hexbytes(msg.data)} "
              f"every {self.period * 1000:.0f} ms  "
              f"(display={self.payload[0]} button={self.payload[1]} "
              f"b2=0x{self.payload[2]:02X})")

    def _stop_illum(self):
        if self.illum_task is not None:
            self.illum_task.stop()
            self.illum_task = None

    def _stop_sweep(self):
        if self.sweep_thread and self.sweep_thread.is_alive():
            self.sweep_stop.set()
            self.sweep_thread.join()

    def _args(self, line, n_min, n_max, usage):
        args = shlex.split(line)
        if not n_min <= len(args) <= n_max:
            raise ValueError(f"usage: {usage}")
        return args

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except (ValueError, can.CanError) as e:
            print(f"error: {e}")
            return False

    def emptyline(self):
        pass

    # -- commands: illumination --------------------------------------------

    def do_on(self, line):
        """on — send display/button at the last non-zero level (default 0x64)."""
        self._stop_sweep()
        self.payload[0:2] = self.on_level
        self._apply()

    def do_off(self, line):
        """off — send 00 00 on display and button (byte 2 unchanged)."""
        self._stop_sweep()
        self.payload[0:2] = [0x00, 0x00]
        self._apply()

    def _set(self, idx, line, usage):
        (v,) = self._args(line, 1, 1, usage)
        v = parse_byte(v)
        self._stop_sweep()
        for i in idx:
            self.payload[i] = v
        if any(self.payload[0:2]):
            self.on_level = list(self.payload[0:2])
        self._apply()

    def do_level(self, line):
        """level N — set display AND button to N.
        N: decimal (0..255), hex (0x40 / 40h) or percent of 0x64 (50%)."""
        self._set([0, 1], line, "level N")

    def do_display(self, line):
        """display N — set byte 0 (display backlight) only."""
        self._set([0], line, "display N")

    def do_button(self, line):
        """button N — set byte 1 (front-panel button backlight) only."""
        self._set([1], line, "button N")

    def do_b2(self, line):
        """b2 N — set byte 2 (meaning unknown)."""
        self._set([2], line, "b2 N")

    def do_raw(self, line):
        """raw B0 B1 B2 — set the whole 0x635 payload, e.g. `raw 00 ff 00`.
        Bare tokens here are read as hex."""
        self._stop_sweep()
        args = self._args(line, 3, 3, "raw B0 B1 B2")
        self.payload = [int(a.lower().removeprefix("0x"), 16) & 0xFF for a in args]
        self._apply()

    def do_stop(self, line):
        """stop — stop transmitting 0x635 (0x271 is left alone)."""
        self._stop_sweep()
        self._stop_illum()
        print("[tx] 0x635 stopped")

    def do_period(self, line):
        """period MS — change the 0x635 repetition period."""
        (ms,) = self._args(line, 1, 1, "period MS")
        ms = float(ms)
        if ms < 10:
            raise ValueError("period below 10 ms is not sensible on a 100k bus")
        self.period = ms / 1000
        if self.illum_task is not None:
            self._stop_illum()
            self._apply()
        else:
            print(f"period set to {ms:.0f} ms (applies on next send)")

    def do_once(self, line):
        """once — send the current 0x635 payload a single time, not periodically."""
        self.bus.send(self._illum_msg())
        print(f"[tx] 0x{ILLUM_ID:03X} {hexbytes(self.payload)} (single)")

    def do_sweep(self, line):
        """sweep FIELD START END [STEP] [DWELL_S] — ramp one byte in the background.
        FIELD is display, button, both or b2. Defaults: STEP 1, DWELL 0.5 s.
        Example (CANBUS.md T6): sweep button 0 0x64 1 0.5
        Any other illumination command, or `stop`, aborts the sweep."""
        args = self._args(line, 3, 5, "sweep FIELD START END [STEP] [DWELL_S]")
        fields = {"display": [0], "button": [1], "both": [0, 1], "b2": [2]}
        if args[0] not in fields:
            raise ValueError(f"FIELD must be one of {', '.join(fields)}")
        idx = fields[args[0]]
        start, end = parse_byte(args[1]), parse_byte(args[2])
        step = int(args[3], 0) if len(args) > 3 else 1
        dwell = float(args[4]) if len(args) > 4 else 0.5
        if step <= 0:
            raise ValueError("STEP must be positive")
        values = list(range(start, end + 1, step) if end >= start
                      else range(start, end - 1, -step))

        self._stop_sweep()
        self.sweep_stop.clear()

        def run():
            for v in values:
                if self.sweep_stop.is_set():
                    print("\n[sweep] aborted")
                    return
                for i in idx:
                    self.payload[i] = v
                self._apply()
                self.sweep_stop.wait(dwell)
            print("\n[sweep] done; holding last value")

        print(f"[sweep] {args[0]} {start}→{end} step {step}, "
              f"{dwell}s each, {len(values)} steps (~{len(values) * dwell:.0f}s)")
        self.sweep_thread = threading.Thread(target=run, daemon=True)
        self.sweep_thread.start()

    # -- commands: keep-alive ----------------------------------------------

    def do_ign(self, line):
        """ign on|off — transmit 0x271 = 01 80 every 100 ms (CANBUS.md §4, T5)."""
        (state,) = self._args(line, 1, 1, "ign on|off")
        if state == "on":
            if self.ign_task is None:
                msg = can.Message(arbitration_id=IGNITION_ID, data=IGNITION_ON,
                                  is_extended_id=False)
                self.ign_task = self.bus.send_periodic(msg, IGNITION_PERIOD)
            print(f"[tx] 0x{IGNITION_ID:03X} {hexbytes(IGNITION_ON)} every 100 ms")
        elif state == "off":
            if self.ign_task is not None:
                self.ign_task.stop()
                self.ign_task = None
            print(f"[tx] 0x{IGNITION_ID:03X} stopped")
        else:
            raise ValueError("usage: ign on|off")

    def do_nm(self, line):
        """nm on [NODE] | off — act as a second NM node so the unit leaves
        limp-home. NODE is our node number (default 0x00, i.e. ID 0x420);
        the unit is node 0x16. Ring formed = the unit sends `00 01` every
        100 ms, and `status` says "ring up"."""
        args = self._args(line, 1, 2, "nm on [NODE] | nm off")
        if args[0] == "on":
            node = parse_byte(args[1]) if len(args) > 1 else 0x00
            if node == HEAD_UNIT_NODE or NM_BASE + node > 0x7FF:
                raise ValueError(f"node 0x{node:02X} is not usable")
            self._stop_nm()
            self.nm = NmPeer(self.bus, node)
            self.notifier.add_listener(self.nm)
            self.nm.start()
            print(f"[nm] node 0x{node:02X} (ID 0x{self.nm.arb_id:03X}) joined")
        elif args[0] == "off":
            self._stop_nm()
            print("[nm] stopped")
        else:
            raise ValueError("usage: nm on [NODE] | nm off")

    def _stop_nm(self):
        if self.nm is not None:
            self.notifier.remove_listener(self.nm)
            self.nm.stop()
            self.nm = None

    # -- commands: observation ---------------------------------------------

    def do_mon(self, line):
        """mon on|off|all — received-frame printing. `all` prints every frame,
        not just changes (noisy: the unit sends 0x436 every 500 ms)."""
        (state,) = self._args(line, 1, 1, "mon on|off|all")
        if state not in ("on", "off", "all"):
            raise ValueError("usage: mon on|off|all")
        self.monitor.enabled = state != "off"
        self.monitor.show_all = state == "all"
        print(f"monitor {state}")

    def do_status(self, line):
        """status — what is being transmitted, and what has been received."""
        illum = (f"{hexbytes(self.payload)} every {self.period * 1000:.0f} ms"
                 if self.illum_task else "not sending")
        sweeping = self.sweep_thread is not None and self.sweep_thread.is_alive()
        print(f"  0x{ILLUM_ID:03X}  {illum}{'  (sweeping)' if sweeping else ''}")
        print(f"  0x{IGNITION_ID:03X}  "
              f"{'01 80 every 100 ms' if self.ign_task else 'not sending'}")
        if self.nm:
            st = self.nm.stats
            print(f"  0x{self.nm.arb_id:03X}  NM node 0x{self.nm.node:02X}: "
                  f"sent {st['alive']} alive, {st['ring']} ring; "
                  f"{st['ring_rx']} rings from the unit — "
                  f"ring {'UP' if self.nm.ring_up else 'down'}")
            with self.nm.lock:
                seen = sorted(self.nm.seen.items())
            for (succ, op), n in seen:
                name = NM_OPCODES.get(op, f"op 0x{op:02X}")
                print(f"         unit → node 0x{succ:02X} {name:<20} ×{n}")
        else:
            print("  NM     not participating")
        with self.monitor.lock:
            seen = sorted(self.monitor.counts.items())
            last = dict(self.monitor.last)
        if not seen:
            print("  rx: nothing received")
        for arb, n in seen:
            note = describe_nm(last[arb]) if arb == HEAD_UNIT_NM_ID else ""
            print(f"  rx 0x{arb:03X}  ×{n:<6} last {hexbytes(last[arb]):<24}{note}")

    def do_quit(self, line):
        """quit — stop all transmission and exit."""
        return True

    do_exit = do_quit
    do_EOF = do_quit


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--channel", default="can0")
    ap.add_argument("--period", type=float, default=200,
                    help="0x635 repetition period in ms (default 200)")
    ap.add_argument("--ign", action="store_true",
                    help="start the 0x271 keep-alive immediately")
    ap.add_argument("--nm", type=parse_byte, metavar="NODE",
                    help="join NM as NODE immediately (e.g. --nm 0)")
    ap.add_argument("--quiet", action="store_true",
                    help="start with the receive monitor off")
    args = ap.parse_args()

    try:
        bus = can.Bus(interface="socketcan", channel=args.channel)
    except (OSError, can.CanError) as e:
        sys.exit(f"cannot open {args.channel}: {e}\n"
                 f"is it up?  sudo ip link set {args.channel} up type can bitrate 100000")

    monitor = Monitor()
    monitor.enabled = not args.quiet
    notifier = can.Notifier(bus, [monitor])
    console = Console(bus, monitor, args.period / 1000)
    console.notifier = notifier
    try:
        if args.nm is not None:
            console.do_nm(f"on {args.nm}")
        if args.ign:
            console.do_ign("on")
        console.cmdloop()
    except KeyboardInterrupt:
        print()
    finally:
        console._stop_sweep()
        console._stop_nm()
        bus.stop_all_periodic_tasks()
        notifier.stop()
        bus.shutdown()
        print("all transmission stopped")


if __name__ == "__main__":
    main()
