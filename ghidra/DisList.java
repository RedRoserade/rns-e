// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Force-disassemble at given seed addresses, then list ranges: args = outfile seedsCSV start1 end1 [...]
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class DisList extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        if (!a[1].equals("-")) for (String s : a[1].split(",")) disassemble(toAddr(s));
        for (int k = 2; k + 1 < a.length; k += 2) {
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
