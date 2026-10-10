// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Print disassembly for address ranges: args = outfile start1 end1 [start2 end2 ...]
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class Listing extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        for (int k = 1; k + 1 < a.length; k += 2) {
            AddressSet set = new AddressSet(toAddr(a[k]), toAddr(a[k+1]));
            out.println("---- " + a[k] + ".." + a[k+1]);
            for (Instruction i : currentProgram.getListing().getInstructions(set, true)) {
                StringBuilder refs = new StringBuilder();
                for (var r : i.getReferencesFrom()) refs.append(" ->").append(r.getToAddress());
                out.println(i.getAddress() + "  " + i + refs);
            }
        }
        out.close();
    }
}
