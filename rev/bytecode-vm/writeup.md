
# Official Writeup — Aurora License VM (Reverse Engineering)

**Category:** Reverse Engineering &nbsp;|&nbsp; **Difficulty:** Hard &nbsp;|&nbsp;
**Flag:** `flag{by73c0d3_vm_z3_pwn}`

## Concept

This is a **VM-reversing** challenge. Rather than obfuscating native code,
the binary implements a tiny custom virtual machine — a stack-based
bytecode interpreter — and the license check is written *in that
bytecode*, not in x86. To solve it you have to reverse-engineer a machine
that doesn't exist anywhere else before you can even begin reading the
check it runs.

The intended path has three distinct stages, escalating in what they
demand of you:

1. **Recover the instruction set** by reversing the dispatch loop.
2. **Extract the embedded bytecode program** (the actual check).
3. **Solve the constraint system** the bytecode represents — the coupled
   byte operations are painful by hand but trivial for an SMT solver like
   z3 (or a symbolic-execution engine like angr).

## Why build a VM instead of obfuscating native code?

Native obfuscation (packing, opaque predicates, control-flow flattening)
hides *known* semantics. A custom VM does something more interesting: it
forces the solver to first discover an *entirely new* instruction set
with no documentation, no standard tooling, and no disassembler that
understands it. This is a recognized top-tier RE category precisely
because you can't lean on Ghidra/IDA to do the semantic lifting for you —
the tool disassembles the *interpreter*, but the *program* the
interpreter runs is just an opaque byte array until you've reconstructed
the ISA yourself. Building one from scratch — inventing the opcodes,
their stack effects, and the check logic — is what makes this a design
exercise rather than an obfuscation exercise.

## Stage 1 — Recover the instruction set

Loading `vm` in a disassembler and finding `main`, you reach a function
that reads a byte array and switches on each byte. The dispatch loop is a
chain of comparisons against opcode values:

```asm
cmp    $0x30, %al        ; OP_EQ
cmp    $0x20, %al        ; OP_XOR
cmp    $0x10, %al        ; OP_PUSHI
...
```

Working through each case and its stack manipulation recovers the full
ISA. It's a stack machine with a small register file (unused by this
program) and these opcodes:

| Opcode | Mnemonic | Effect |
|--------|----------|--------|
| `0x10` | `PUSHI imm` | push immediate byte |
| `0x11` | `LOAD imm`  | push `input[imm]` |
| `0x20` | `XOR`  | `a=pop; b=pop; push a^b` |
| `0x21` | `ADD`  | `a=pop; b=pop; push (a+b)&0xff` |
| `0x22` | `SUB`  | `a=pop; b=pop; push (b-a)&0xff` |
| `0x23` | `ROL`  | `a=pop; b=pop; push rotl8(b, a&7)` |
| `0x24` | `MUL`  | `a=pop; b=pop; push (a*b)&0xff` |
| `0x30` | `EQ`   | `a=pop; b=pop; fail unless a==b` |
| `0xff` | `HALT` | success |

The important detail: `EQ` is the only thing that can cause failure. The
program is a straight-line sequence of "compute something from the input,
assert it equals a constant."

## Stage 2 — Extract the bytecode

The `program[]` array lives in the binary's data section. From the ISA
you know the structure: the check is 24 repetitions (one per flag byte)
of the pattern

```
LOAD i ; PUSHI key_i ; XOR ; PUSHI c_i ; ADD ; PUSHI r_i ; ROL ; PUSHI k_i ; EQ
```

terminated by `HALT`. Dumping the array (e.g. in gdb, or by carving the
data section) gives you, for each index `i`, the three immediates
`key_i`, `c_i`, `r_i` and the expected result `k_i`. That's everything
needed to reconstruct the constraints.

The per-byte constraint is:

```
rotl8( ((input[i] XOR key_i) + c_i) & 0xff , r_i )  ==  k_i
```

## Stage 3 — Solve the constraints

Each constraint is individually invertible (XOR, add, and rotate are all
reversible byte operations), so in principle you could invert all 24 by
hand. In practice, doing that correctly 24 times — tracking the rotate
direction, the modular add, and the XOR key at each index — is exactly
the kind of error-prone manual work that symbolic tooling exists to
eliminate. The clean solve is to model each byte as an 8-bit variable and
hand the whole system to z3:

```python
from z3 import BitVec, BitVecVal, RotateLeft, Solver, sat

# ... parse program[] into opcodes ...
inp = [BitVec(f"c{i}", 8) for i in range(24)]
s = Solver()
for c in inp:
    s.add(c >= 0x20, c <= 0x7e)          # printable ASCII

# symbolically execute the bytecode, turning each EQ into a constraint
# (see solution/solve.py for the full interpreter loop)

assert s.check() == sat
m = s.model()
print("".join(chr(m[c].as_long()) for c in inp))
# -> flag{by73c0d3_vm_z3_pwn}
```

`solution/solve.py` implements the full symbolic interpreter: it walks the
same bytecode the VM does, but with z3 `BitVec`s in place of concrete
input bytes, accumulating each `EQ` as an `==` constraint. z3 returns the
satisfying assignment — the flag — in milliseconds.

An `angr` solve works too: set the input as symbolic, constrain the
success path (the `"Access granted."` branch), and let its symbolic
executor walk the interpreter. z3 is the lighter-weight route here since
we can read the constraints straight off the bytecode.

## Design decisions worth explaining

**Absolute anchoring for a unique solution.** The single most important
design property is that the flag must be the *unique* solution — if the
constraint system had multiple satisfying inputs, a solver couldn't know
which one is the real flag, and the challenge would be broken. My first
version coupled each byte only to its neighbour (`input[i]` vs
`input[i+1]`), which left the system under-determined: z3 happily returned
a *different* 24-byte string that also passed the VM. I caught this by
having the solver run against the compiled binary and testing its output
— the "solution" was accepted by `vm` but wasn't the flag. The fix was to
anchor each byte to a fixed key-stream constant rather than to another
input byte, which pins every byte to exactly one value. I verified
uniqueness formally by asking z3 for a *second* solution after blocking
the first — it returned UNSAT, proving the flag is the only printable
answer.

**Solver-friendly, not brute-force.** The check deliberately avoids a
single whole-input hash (which would degrade to brute force and test
patience rather than skill). Per-byte reversible constraints keep the
problem in the sweet spot: too tedious to want to do by hand, instant for
an SMT solver — which is precisely the skill this category is meant to
teach, namely *recognizing when to reach for symbolic tooling*.

**`-O2` and stripping.** Optimising and stripping removes symbol names and
inlines the helpers, so the reverser genuinely has to reconstruct the ISA
from the comparison chain rather than reading function names. The flag
never appears in plaintext (`strings vm | grep flag` returns nothing) — it
only exists implicitly in the transformed constants, so it *must* be
solved for, not extracted.

## Lessons for challenge design

The under-determination bug is the whole story here. A VM-reversing
challenge can look completely finished — it compiles, it accepts the real
flag, it rejects obvious wrong guesses — and still be fundamentally broken
because the *check* it runs doesn't uniquely identify the flag. The only
way to catch that is to actually run the intended solver and confirm it
returns *the* flag and not just *a* passing input, then prove uniqueness
explicitly. Designing the constraint system is the real work; wiring up
the VM around it is the easy part.
