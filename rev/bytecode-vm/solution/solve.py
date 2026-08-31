#!/usr/bin/env python3
"""
Official solver for the Aurora License VM (rev).

Models the recovered bytecode semantics as a z3 constraint system and
solves for the flag. Encodes only the recovered opcode semantics (stage 1)
and the embedded bytecode bytes (stage 2); z3 recovers the input (stage 3).

Usage:
    python3 solve.py [path/to/bytecode.inc]
"""
import re
import sys
from z3 import BitVec, BitVecVal, RotateLeft, Solver, sat, simplify

FLAG_LEN = 24

OP_PUSHI, OP_LOAD = 0x10, 0x11
OP_XOR, OP_ADD, OP_SUB, OP_ROL, OP_MUL = 0x20, 0x21, 0x22, 0x23, 0x24
OP_EQ, OP_HALT = 0x30, 0xff


def load_program(path):
    text = open(path).read()
    return [int(b, 16) for b in re.findall(r"0x[0-9a-fA-F]{2}", text)]


def as_bv(x):
    return BitVecVal(x, 8) if isinstance(x, int) else x


def symbolic_run(program, inp, solver):
    stack = []
    pc = 0
    while pc < len(program):
        op = program[pc]; pc += 1
        if op == OP_PUSHI:
            stack.append(as_bv(program[pc])); pc += 1
        elif op == OP_LOAD:
            stack.append(inp[program[pc]]); pc += 1
        elif op == OP_XOR:
            a = stack.pop(); b = stack.pop(); stack.append(a ^ b)
        elif op == OP_ADD:
            a = stack.pop(); b = stack.pop(); stack.append(a + b)
        elif op == OP_SUB:
            a = stack.pop(); b = stack.pop(); stack.append(b - a)
        elif op == OP_ROL:
            a = stack.pop(); b = stack.pop()
            cnt = a.as_long() & 7 if hasattr(a, "as_long") else int(simplify(a).as_long()) & 7
            stack.append(RotateLeft(b, cnt))
        elif op == OP_MUL:
            a = stack.pop(); b = stack.pop(); stack.append(a * b)
        elif op == OP_EQ:
            a = stack.pop(); b = stack.pop(); solver.add(a == b)
        elif op == OP_HALT:
            break
        else:
            raise ValueError(f"unknown opcode 0x{op:02x} at pc={pc-1}")


def solve(program):
    inp = [BitVec(f"c{i}", 8) for i in range(FLAG_LEN)]
    s = Solver()
    for c in inp:
        s.add(c >= 0x20, c <= 0x7e)
    symbolic_run(program, inp, s)
    if s.check() != sat:
        print("[-] UNSAT - constraints unsatisfiable (model wrong or bytecode misread)")
        return None
    m = s.model()
    flag = "".join(chr(m[c].as_long()) for c in inp)
    print(f"[+] FLAG: {flag}")
    return flag


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../challenge/src/bytecode.inc"
    solve(load_program(path))
