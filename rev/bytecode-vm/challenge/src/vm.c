/*
 * Aurora License VM  -  a tiny stack+register bytecode interpreter.
 *
 * The binary embeds a bytecode program (the "license check") that reads
 * the user-supplied flag, runs a sequence of interdependent byte
 * operations over it, and reports success only if every constraint holds.
 *
 * The intended solve: reverse the dispatch loop to recover the opcode
 * semantics (stage 1), extract the embedded bytecode + constants
 * (stage 2), then model the constraints and let z3/angr solve for the
 * input (stage 3). Solving by hand is deliberately painful because the
 * constraints are interdependent across input bytes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define FLAG_LEN 24
#define STACK_SZ 64
#define NUM_REGS 8

/* ---- opcodes (this is exactly what the solver must recover from asm) ---- */
enum {
    OP_PUSHI = 0x10,  /* push immediate byte            */
    OP_LOAD  = 0x11,  /* push input[imm]                */
    OP_XOR   = 0x20,  /* a=pop,b=pop; push (a ^ b)      */
    OP_ADD   = 0x21,  /* a=pop,b=pop; push (a + b)&0xff */
    OP_SUB   = 0x22,  /* a=pop,b=pop; push (b - a)&0xff */
    OP_ROL   = 0x23,  /* a=pop (cnt), b=pop; rotl8(b,a) */
    OP_MUL   = 0x24,  /* a=pop,b=pop; push (a*b)&0xff   */
    OP_EQ    = 0x30,  /* a=pop,b=pop; fail unless a==b  */
    OP_HALT  = 0xff
};

static uint8_t rotl8(uint8_t v, uint8_t c) {
    c &= 7;
    return (uint8_t)((v << c) | (v >> (8 - c)));
}

/*
 * The embedded bytecode program. Structure per constraint:
 *   LOAD i ; <ops with immediates> ; PUSHI k ; EQ
 * meaning: f(input[i], ...) == k
 *
 * These constants were generated from the real flag by build_bytecode.py.
 * (Placeholder here; the build script rewrites this array.)
 */
static uint8_t program[] = {
/*BYTECODE*/
    OP_HALT
};

static int run(const uint8_t *input) {
    uint8_t stack[STACK_SZ];
    int sp = 0;
    size_t pc = 0;
    while (1) {
        uint8_t op = program[pc++];
        switch (op) {
            case OP_PUSHI: stack[sp++] = program[pc++]; break;
            case OP_LOAD:  stack[sp++] = input[program[pc++]]; break;
            case OP_XOR: { uint8_t a=stack[--sp], b=stack[--sp]; stack[sp++]=a^b; } break;
            case OP_ADD: { uint8_t a=stack[--sp], b=stack[--sp]; stack[sp++]=(uint8_t)(a+b); } break;
            case OP_SUB: { uint8_t a=stack[--sp], b=stack[--sp]; stack[sp++]=(uint8_t)(b-a); } break;
            case OP_ROL: { uint8_t a=stack[--sp], b=stack[--sp]; stack[sp++]=rotl8(b,a); } break;
            case OP_MUL: { uint8_t a=stack[--sp], b=stack[--sp]; stack[sp++]=(uint8_t)(a*b); } break;
            case OP_EQ:  { uint8_t a=stack[--sp], b=stack[--sp]; if(a!=b) return 0; } break;
            case OP_HALT: return 1;
            default: return 0;
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <flag>\n", argv[0]);
        return 2;
    }
    if (strlen(argv[1]) != FLAG_LEN) {
        printf("Denied.\n");
        return 1;
    }
    if (run((const uint8_t*)argv[1])) {
        printf("Access granted.\n");
        return 0;
    }
    printf("Denied.\n");
    return 1;
}
