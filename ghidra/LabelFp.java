// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Apply names to the front-panel link and softkey-lamp path (V574 OSM @ 0x80400200).
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
public class LabelFp extends GhidraScript {
    void name(long a, String n, String c) throws Exception {
        var ad = toAddr(a);
        Function f = getFunctionAt(ad);
        if (f == null) { if (getInstructionAt(ad) == null) disassemble(ad); f = createFunction(ad, n); }
        if (f != null) { f.setName(n, SourceType.USER_DEFINED); if (c != null) f.setComment(c); }
        else { createLabel(ad, n, true); if (c != null) setPlateComment(ad, c); }
    }
    public void run() throws Exception {
        // panel link driver (FPDRV)
        name(0x80555e24L, "fpdrv_uart_tx", "Raw UART TX of n bytes. 0x15/0x16/0x18 bypass the wait-for-ACK lock; other frames start the reply timer");
        name(0x80555d3eL, "fpdrv_tx_locked", "0 if free or byte is 0x15/0x16/0x18");
        name(0x80555424L, "fpdrv_rx_loop", "RX: 0x15 = ACK of our frame, 0x18 = panel NAK -> retransmit, else validate + dispatch");
        name(0x80556b68L, "fpdrv_rx_validate", "Error flags: 0x04 HU->panel addr {00 01 02 03 06 07 09 0A 0E} or >=0x13; 0x40 LEN mismatch (tbl 08:6 0B:3 0C:8 0D:6 0F:2 10:3 11:3); 0x01 checksum");
        name(0x805557aaL, "fpdrv_rx_dispatch", "ADDR 0F boot->init, 0C keys, 0D rotary, 04 (ignored), 10, 08/0B/11/12 ack only; else NAK 18 03 80");
        name(0x805556dcL, "fpdrv_send_ack", "Bare 0x15, or 0x16 + next queued frame (piggyback)");
        name(0x80555676L, "fpdrv_send_nak", "18 03 <flags> CK");
        name(0x80555636L, "fpdrv_send_resync", "00 03 2E 31, after 3 failed retries");
        name(0x805551aaL, "fpdrv_reply_timeout", "300 ms reply timer: retry, then resync, then hard reset");
        name(0x805567deL, "fpdrv_init_step", "step 0..4: frames 02, 03, 0A, 09, 06; step 5 done");
        name(0x8055683eL, "fpdrv_tx_01", "01 06 00 28 08 03 3A (no caller found)");
        name(0x805568a6L, "fpdrv_tx_init02", "02 0C 40 1D 4B 42 40 00 40 01 FF 05 7D");
        name(0x8055691aL, "fpdrv_tx_init03", "03 0F 3C 0A 02 0A 04 0A 04 0A 04 0A 04 0A 0A A6");
        name(0x80556998L, "fpdrv_tx_init0A", "0A 07 00 FF 1C FF 1C 47");
        name(0x805569f8L, "fpdrv_tx_init09", "09 06 00 00 0F 06 24");
        name(0x80556a50L, "fpdrv_tx_init06", "06 0E 00 00 00 00 30 70 00 00 00 00 00 00 B4");
        name(0x80603400L, "fp_rx_keys_0C", "6-byte key bitmap -> change detect -> message to UI");
        name(0x8060347cL, "fp_rx_rotary_0D", null);
        // softkey lamps
        name(0x80603056L, "fp_send_lamp_frame", "07 06 <odd bits 15..0> <even bits 15..0> CK from a u32 lamp word");
        name(0x8059a840L, "lamp_update", "Builds u32 lamp word: bits 0,2 CD state; 4,6,8,10 softkey mask bits 0..3; 12,14,16 dimmer flag");
        name(0x8059a7eeL, "lamp_power_ok", "power state 2/3 and two more state checks; else all lamps off");
        name(0x80599410L, "softkey_lamp_set", "state+8 = mask");
        name(0x80599424L, "softkey_lamp_get", null);
        name(0x805b60f8L, "screen_softkey_lamp", "table 0x8046B0C0 {u16 screen, u16 mask}; 0xF = leave unchanged; screens 0x6D/0x6E computed");
        name(0x805a1752L, "softkey_lamp_apply", null);
    }
}
