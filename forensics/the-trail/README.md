# The Trail — Forensics (Easy → Hard)

> Someone on the Aurora team leaked something. We pulled a few artifacts
> off the compromised host. Follow the trail and find out what walked out
> the door.

## Description

This is a **multi-stage** forensics challenge. You're given a handful of
artifacts recovered from a compromised host. Each one, worked correctly,
tells you where to look next. There is **one flag**, at the very end of
the chain.

No brute force is required at any stage — every step has a clean,
intended technique. If you find yourself brute forcing, step back and
look at the artifact again.

## Artifacts (`challenge/files/`)

| File | What it is |
|---|---|
| `AURORA_README.md` | A project readme pulled off the host. Looks ordinary. |
| `capture.pcap` | A network capture from the host during the incident. |
| `aurora.dmp` | A chunk of process memory dumped from the host. |
| `aurora-config-repo.tar.gz` | An archived copy of an internal git repo. |

> **Important:** extract `aurora-config-repo.tar.gz` locally and work
> inside the extracted directory. Do not re-clone or re-push it anywhere
> before solving — some of what you need does not survive a `git clone`.

## Where to start

Start with `AURORA_README.md`. It looks like a completely normal project
readme... which is exactly why it's worth a second, closer look. What
does a text file contain that you can't see when you just read it?

## Flag format

`flag{...}`

---
*Category: Forensics · Difficulty: Easy → Hard (4 stages) · Points: 500*
