// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Decompile every function whose entry lies in [start,end]: args = outfile start end
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class DumpRange extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
        AddressSet set = new AddressSet(toAddr(a[1]), toAddr(a[2]));
        for (Function f : currentProgram.getFunctionManager().getFunctions(set, true)) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            out.println("\n==== " + f.getName() + " @ " + f.getEntryPoint());
            out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// failed");
        }
        out.close();
    }
}
