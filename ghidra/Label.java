// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Apply names to the 0x635 dimming path (V574 OSM @ 0x80400200).
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
public class Label extends GhidraScript {
    void name(long a, String n, String c) throws Exception {
        var ad = toAddr(a);
        Function f = getFunctionAt(ad);
        if (f == null) { Function g = getFunctionContaining(ad); if (g != null && !g.getEntryPoint().equals(ad)) { /* split: recreate */ }
            disassemble(ad); f = createFunction(ad, n); }
        if (f != null) { f.setName(n, SourceType.USER_DEFINED); if (c != null) f.setComment(c); }
        else println("could not create " + n);
    }
    public void run() throws Exception {
        name(0x80665f94L, "can_rx_register", "CAN receive registration. r4=handle, r5=desc {u16 type; u16 id; void(*cb); u8 *buf; u16 len}");
        name(0x80604278L, "dim_init", null);
        name(0x8060431aL, "dim_register_0x635", "Registers CAN 0x635, len 3, cb=dim_can_rx_0x635, buf=0x8e9ede79");
        name(0x8060463eL, "dim_can_rx_0x635", "CAN 0x635 callback: r6 = 3 data bytes. Stores b0,b1; checks b1 (KL58s)");
        name(0x806046c6L, "dim_check_kl58s", "byte1 > 0x7E -> 'KL58S ERROR', error counter at state+0xE");
        name(0x806049a2L, "kl58s_invalid", "returns b > 0x7E");
        name(0x8060498cL, "dimval_invalid", "returns !(5 < b < 0x7F)");
        name(0x80604874L, "dim_sanitize", "(b0,b1) -> validate, substitute last-good or default 0x50 -> dim_set_levels");
        name(0x806056dcL, "dim_store_raw", "state+0x14 = b0, state+0x15 = b1");
        name(0x8060570aL, "dim_get_raw", null);
        name(0x8060577eL, "dim_set_levels", "state+0x17 = display, state+0x18 = KL58s");
        name(0x8060573cL, "dim_get_levels", null);
        name(0x806049acL, "dim_calc_pwm", "levels -> two PWM values via dim_curve_ab");
        name(0x80605030L, "dim_curve_ab", null);
        name(0x806051f6L, "dim_curve_display", "0..100 -> 0..0x9B0");
        name(0x80605168L, "fp_set_dimmer", null);
        name(0x8060530cL, "fp_send_dim_frame", "Builds panel frame 06 0E <12 bytes> <sum> and posts to mailbox 0x14");
        name(0x8060360eL, "fp_checksum", "additive sum of n-1 bytes");
        name(0x80602fc0L, "fp_txbuf_alloc", "16 x 0x20 pool, '[FP] GET ERROR' when full");
    }
}
