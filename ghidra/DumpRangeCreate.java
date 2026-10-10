// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Like DumpRange, but first creates functions at every SH prologue in [start,end]: args = outfile start end
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class DumpRangeCreate extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        Address s = toAddr(a[1]), e = toAddr(a[2]);
        for (Address p = s; p.compareTo(e) < 0; p = p.add(2)) {
            int w = getShort(p) & 0xffff;
            if (w != 0x4f22) continue;                       // sts.l pr,@-r15
            Address q = p;
            while (((getShort(q.subtract(2)) & 0xff0f) == 0x2f06)) q = q.subtract(2); // mov.l rN,@-r15
            if (getFunctionContaining(q) != null && getFunctionContaining(q).getEntryPoint().equals(q)) continue;
            if (getInstructionAt(q) == null) disassemble(q);
            if (getFunctionAt(q) == null) createFunction(q, null);
        }
        DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
        for (Function f : currentProgram.getFunctionManager().getFunctions(new AddressSet(s, e), true)) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            out.println("\n==== " + f.getName() + " @ " + f.getEntryPoint());
            out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// failed");
        }
        out.close();
    }
}
