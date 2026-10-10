// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Decompile every function that references any of the given addresses: args = outfile addr...
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
public class Callers extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
        Set<Function> done = new LinkedHashSet<>();
        for (int k = 1; k < a.length; k++) {
            out.println("######## refs to " + a[k]);
            for (Reference r : getReferencesTo(toAddr(a[k]))) {
                Function f = getFunctionContaining(r.getFromAddress());
                out.println("# " + r.getFromAddress() + " " + r.getReferenceType() + " in " + (f == null ? "?" : f.getName() + "@" + f.getEntryPoint()));
                if (f != null) done.add(f);
            }
        }
        for (Function f : done) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            out.println("\n==== " + f.getName() + " @ " + f.getEntryPoint());
            out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// failed");
        }
        out.close();
    }
}
