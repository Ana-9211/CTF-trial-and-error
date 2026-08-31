# Build-Your-Own CTF

A set of self-designed CTF challenges, built rather than solved. Each one
includes the vulnerable challenge itself, an automated solve script that
proves the intended path actually works, and an official writeup
explaining the vulnerability class, the design decisions behind it, and
how it maps to real-world incidents.

The premise: solving a challenge someone else built proves you can find
a known pattern. Designing one — deciding exactly where the flaw lives,
building a working exploit path around it, and being able to explain
*why* it breaks — proves you understand the underlying mechanism well
enough to construct it from scratch.

## Challenges

| Category | Name | Vulnerability | Difficulty | Status |
|---|---|---|---|---|
| Web | [SSRF / DocuRender](web/ssrf/) | SSRF — blocklist bypass via numeric IP encoding | Medium | ✅ |
| Crypto | [RSA Broadcast](crypto/rsa-broadcast/) | Franklin-Reiter related-message attack | Medium | ✅ |
| Forensics | [The Trail](forensics/the-trail/) | 4-stage chain: whitespace stego → DNS tunneling → memory forensics → git history | Easy → Hard | ✅ |
| Rev | [Bytecode VM](rev/bytecode-vm/) | Reverse a bespoke bytecode VM, solve via symbolic execution | Hard | ✅ |

## Structure

Each challenge folder follows the same layout:

```
category/challenge-name/
├── README.md       # player-facing description (no spoilers)
├── challenge/       # everything needed to run the challenge locally
├── solution/        # automated solve script proving the intended path
└── writeup.md       # official technical writeup (spoilers)
```

## Running a challenge

Each challenge's own README has exact instructions, but generally:

```bash
cd category/challenge-name/challenge
docker compose up --build
```
