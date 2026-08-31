# Bytecode VM — Reverse Engineering (Hard)

> Our licensing check is bulletproof. It runs your key through our
> proprietary virtual machine. Good luck forging one.

## Description

`vm` is a license checker. Give it a key and it tells you whether access
is granted:

```bash
./vm 'your_guess_here'
# Denied.
```

There's exactly one key it accepts, and that key is the flag. The binary
is stripped. It doesn't check your input directly — it runs a small
embedded **bytecode program** inside a custom virtual machine, and only
that program knows what a valid key looks like.

## What you're given (`challenge/files/`)

- `vm` — the license checker (stripped x86-64 ELF)

## The shape of it (no spoilers)

Three things stand between you and the flag:

1. The VM's instruction set isn't documented anywhere. You'll have to
   recover what each opcode does from the dispatch loop.
2. The actual check is data, not code — a bytecode program embedded in
   the binary.
3. Once you understand both, the check is a system of constraints on the
   input bytes. Solving it by hand is... not recommended.

## Flag format

`flag{...}` (24 characters, including the braces)

---
*Category: Reverse Engineering · Difficulty: Hard · Points: 500*
