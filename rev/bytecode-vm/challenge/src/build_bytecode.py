"""
Generates the embedded bytecode for vm.c from the real flag.

Constraint design (UNIQUELY solvable, still symbolic-exec friendly):
  Each flag byte is tied to an ABSOLUTE expected constant through a chain
  of reversible byte ops, so the system has exactly one printable-ASCII
  solution. The "hard by hand" property comes from the op chain being
  non-obvious to invert manually (XOR with a rolling key, add, rotate),
  NOT from leaving the system under-determined.

  For each i:
      k_i = i-th byte of a rolling key stream (deterministic)
      t = input[i] XOR k_i
      t = (t + C[i]) & 0xff
      t = rotl8(t, R[i])
      constraint:  t == K[i]      where K[i] computed from the real flag

  Because k_i is a fixed constant (not another input byte), each
  constraint pins input[i] to exactly one value -> unique solution.
  The chain is still annoying to invert by hand across 24 bytes, but z3
  solves it instantly.
"""
import json

FLAG = b"flag{by73c0d3_vm_z3_pwn}"   # 24 chars
LEN = len(FLAG)

OP_PUSHI = 0x10
OP_LOAD  = 0x11
OP_XOR   = 0x20
OP_ADD   = 0x21
OP_SUB   = 0x22
OP_ROL   = 0x23
OP_MUL   = 0x24
OP_EQ    = 0x30
OP_HALT  = 0xff

def rotl8(v, c):
    c &= 7
    return ((v << c) | (v >> (8 - c))) & 0xff

# deterministic rolling key stream (fixed constants baked into bytecode)
KEY = [(0x5a ^ (i * 0x2d + 0x13)) & 0xff for i in range(LEN)]
C   = [(0x11 * (i + 1)) & 0xff for i in range(LEN)]
R   = [(i % 7) for i in range(LEN)]

def expected_k(i):
    t = FLAG[i] ^ KEY[i]
    t = (t + C[i]) & 0xff
    t = rotl8(t, R[i])
    return t

program = []
for i in range(LEN):
    program += [OP_LOAD, i]            # push input[i]
    program += [OP_PUSHI, KEY[i]]      # push key
    program += [OP_XOR]                # input[i] ^ key
    program += [OP_PUSHI, C[i]]        # push C
    program += [OP_ADD]                # + C
    program += [OP_PUSHI, R[i]]        # push rotate count
    program += [OP_ROL]                # rotl
    program += [OP_PUSHI, expected_k(i)]
    program += [OP_EQ]                 # == K[i]
program += [OP_HALT]

assert LEN == 24, f"FLAG must be 24 chars, got {LEN}"

# emit C array text
lines, row = [], []
for b in program:
    row.append(f"0x{b:02x}")
    if len(row) == 12:
        lines.append("    " + ", ".join(row) + ",")
        row = []
if row:
    lines.append("    " + ", ".join(row) + ",")
with open("bytecode.inc", "w") as f:
    f.write("\n".join(lines) + "\n")

with open("constants.json", "w") as f:
    json.dump({"FLAG": FLAG.decode(), "LEN": LEN, "KEY": KEY, "C": C, "R": R,
               "K": [expected_k(i) for i in range(LEN)],
               "program_len": len(program)}, f, indent=2)

print(f"flag        : {FLAG.decode()}")
print(f"program len : {len(program)} bytes")
print("bytecode.inc + constants.json written")
