// SPDX-FileCopyrightText: 2026 André Carvalho
// SPDX-License-Identifier: Apache-2.0
// Decompile functions containing given addresses, plus callers/callees to a given depth.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;
import java.io.*;

public class Dump extends GhidraScript {
    DecompInterface di;
    Set<Function> done = new LinkedHashSet<>();
    PrintWriter out;

    void dump(Function f, String why) throws Exception {
        if (f == null || !done.add(f)) return;
        out.println("\n==================== " + f.getName() + " @ " + f.getEntryPoint() + "  [" + why + "]");
        List<String> callers = new ArrayList<>();
        for (Reference r : getReferencesTo(f.getEntryPoint())) {
            Function c = getFunctionContaining(r.getFromAddress());
            callers.add(r.getFromAddress() + (c != null ? "(" + c.getName() + ")" : "") + ":" + r.getReferenceType());
        }
        out.println("// refs to entry: " + callers);
        DecompileResults res = di.decompileFunction(f, 120, monitor);
        out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// decompile failed: " + res.getErrorMessage());
    }

    Function fnAt(Address a) throws Exception {
        Function f = getFunctionContaining(a);
        if (f == null) {
            // walk back to a plausible entry and let Ghidra create it
            Instruction i = getInstructionContaining(a);
            if (i == null) { disassemble(a); }
            f = getFunctionContaining(a);
            if (f == null) {
                Address entry = findPrologue(a);
                if (entry != null) { disassemble(entry); f = createFunction(entry, null); }
            }
        }
        return f;
    }
    Address findPrologue(Address a) throws Exception {
        for (int back = 0; back < 0x2000; back += 2) {
            Address p = a.subtract(back);
            int w = getShort(p) & 0xffff;
            if (w == 0x4f22) { // sts.l pr,@-r15; prologue pushes precede it
                Address q = p;
                while (true) { int pw = getShort(q.subtract(2)) & 0xffff; if ((pw & 0xff0f) == 0x2f06) q = q.subtract(2); else break; }
                return q;
            }
        }
        return null;
    }

    public void run() throws Exception {
        String[] a = getScriptArgs();
        out = new PrintWriter(new FileWriter(a[0]));
        int depthUp = Integer.parseInt(a[1]);
        di = new DecompInterface(); di.openProgram(currentProgram);
        for (int k = 2; k < a.length; k++) {
            Address ad = toAddr(a[k]);
            Function f = fnAt(ad);
            dump(f, "contains " + a[k]);
            List<Function> lvl = new ArrayList<>(); if (f != null) lvl.add(f);
            for (int d = 0; d < depthUp; d++) {
                List<Function> nxt = new ArrayList<>();
                for (Function g : lvl) for (Function c : g.getCallingFunctions(monitor)) { nxt.add(c); dump(c, "caller(d" + (d+1) + ") of " + g.getName()); }
                lvl = nxt;
            }
        }
        out.close();
    }
}
