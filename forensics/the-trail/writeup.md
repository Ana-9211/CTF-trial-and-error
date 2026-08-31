
# Official Writeup — The Trail (Forensics, 4-stage chain)

**Category:** Forensics &nbsp;|&nbsp; **Difficulty:** Easy → Hard &nbsp;|&nbsp;
**Flag:** `flag{wh1t3sp4ce_dns_m3m0ry_r3fl0g_full_ch41n_pwn3d}`

## Design philosophy

The point of this challenge isn't any single technique — it's the
*pivot*. Each stage hands you a pointer into the next, and the real skill
being tested is recognizing **what kind of artifact you're holding and
which tool it calls for**. That's the actual day-job of a forensics
analyst: not "run one tool," but "read the situation and know where to
look next." Difficulty ramps deliberately: stage 1 is an on-ramp anyone
can get with a nudge; stage 4 requires understanding git internals well
enough to recover something that was deliberately made to look deleted.

The chain threads a single secret from a text file, through the network
layer, through memory, and finally into version-control internals — four
completely different evidence domains, one continuous investigation.

---

## Stage 1 — Whitespace steganography (easy)

**Artifact:** `AURORA_README.md` — an ordinary-looking project readme.

**The tell:** the file reads as completely normal prose. The trick is
that information is hidden not in the *visible* characters but in the
**trailing whitespace** at the end of lines — invisible in any normal
text viewer.

**Recovery:**

```bash
# reveal trailing whitespace
cat -A AURORA_README.md | grep -E '( |\^I)\$'
# count lines carrying trailing whitespace
grep -cP '[ \t]+$' AURORA_README.md      # -> 136
```

The encoding is classic `stegsnow`-style: each eligible prose line
carries one hidden bit as its final character — a trailing **space = 0**,
a trailing **tab = 1**. Read the eligible lines top to bottom, regroup
the bits 8 at a time (MSB first), and decode to ASCII:

```python
def eligible(line):
    s = line.strip()
    return bool(s) and not s.startswith("#") and not s.startswith(("- ", "* "))

bits = ""
for line in open("AURORA_README.md"):
    line = line.rstrip("\n")
    if not eligible(line):
        continue
    trailing = line[len(line.rstrip()):]
    if trailing:
        bits += "0" if trailing[-1] == " " else "1"

msg = "".join(chr(int(bits[i:i+8], 2)) for i in range(0, len(bits)-7, 8))
print(msg)   # -> exfil.notreal.lab
```

**Output:** the exfil hostname `exfil.notreal.lab`. That's the domain to
hunt for in the next artifact.

*Why this design:* trailing whitespace is genuinely invisible in editors,
survives copy-paste inconsistently (a great real-world detail — it's why
some data-exfil channels use it), and `git diff` famously flags it, which
ties thematically into the git stage later. One bit per line keeps the
encoding clean and tool-recoverable rather than needing a bespoke script.

---

## Stage 2 — DNS tunneling (medium)

**Artifact:** `capture.pcap` — a network capture containing DNS traffic.

**The tell:** most DNS queries in the capture go to normal domains, but a
cluster of them target `exfil.notreal.lab` (the hostname from stage 1)
with long, random-looking leftmost labels — the signature of **DNS
tunneling / exfiltration**.

**Recovery:** filter DNS queries to the tunnel domain, pull the leftmost
label of each (the data-carrying label), order them by the sequence
number embedded as the second label, concatenate, and base32-decode:

```python
from scapy.all import rdpcap, DNSQR
import base64

seen = {}
for p in rdpcap("capture.pcap"):
    if p.haslayer(DNSQR):
        q = p[DNSQR].qname.decode().rstrip(".")
        if q.endswith("exfil.notreal.lab"):
            chunk, seq, *_ = q.split(".")
            seen[int(seq)] = chunk

b32 = "".join(seen[k] for k in sorted(seen))
b32 += "=" * ((-len(b32)) % 8)          # re-pad
print(base64.b32decode(b32).decode())
# -> memory:aurora.dmp marker:AURORA_KEYBLOCK
```

You could equally do this in Wireshark (filter `dns.qry.name contains
"exfil.notreal.lab"`, read the labels off by hand) — the pcap is small
enough. Either way you get the pointer.

**Output:** `memory:aurora.dmp marker:AURORA_KEYBLOCK` — tells you the
next artifact (the memory dump) *and* the exact marker string to search
for inside it.

*Why base32, not base64:* DNS labels are case-insensitive and restricted
to a limited character set, so real DNS tunneling tools use base32
(alphabet `A–Z 2–7`), never base64. Using base32 here isn't a gimmick —
it's the technically correct choice, and recognizing it is part of
knowing what DNS tunneling actually looks like on the wire.

---

## Stage 3 — Memory carving (medium)

**Artifact:** `aurora.dmp` — a chunk of process memory from the host.

**The tell:** stage 2 handed you a marker, `AURORA_KEYBLOCK`. The dump is
mostly binary noise with realistic in-memory string litter (library
paths, HTTP fragments, log lines), and the pointer you need is embedded
as a plaintext block around that marker.

**Recovery:** exactly what an analyst reaches for first on unstructured
memory — `strings` and `grep`:

```bash
strings aurora.dmp | grep -A5 AURORA_KEYBLOCK
```

```
AURORA_KEYBLOCK
repo=aurora-config.git
note=creds rotated; old commit was dropped from main
hint=the secret was committed then removed - check where git keeps
     references that survive a delete (reflog / dangling objects)
AURORA_KEYBLOCK_END
```

`binwalk aurora.dmp` or a hex-editor search for the marker work equally
well.

**Output:** the name of the git repo (`aurora-config`) and an explicit
hint that the secret was committed and then removed — pointing at git's
reflog / dangling objects.

*Design note — why not a real Volatility image:* a full Volatility-format
crash dump would force players to match exact OS build/profile versions,
which is a brittle, environment-specific hurdle that tests setup patience
more than forensic reasoning. A lightweight synthetic blob preserves the
**actual skill** — searching unstructured memory for artifacts with
`strings`/`grep`/`binwalk` — without the profile-matching yak-shave. This
was a deliberate scope decision, documented so nobody mistakes it for a
shortcut taken out of ignorance of Volatility.

---

## Stage 4 — Git reflog / dangling commit recovery (hard)

**Artifact:** `aurora-config-repo.tar.gz` — an archived internal git repo.

**The tell:** stage 3 told you a secret was *committed and then removed*.
A naive look confirms it's gone:

```bash
tar xzf aurora-config-repo.tar.gz && cd aurora-config
git log --oneline --all                 # secret commit is NOT here
git log --all -- secrets.env            # empty - not reachable via any branch
```

The `secrets.env` file isn't in the working tree, isn't on any branch,
and doesn't show up in `git log --all`. It looks genuinely deleted. It
isn't.

**Recovery:** when you commit and then move the branch pointer back (e.g.
`git reset --hard HEAD~1`), the commit becomes **unreferenced** — invisible
to `git log` — but two things still betray it:

1. **The reflog** records every position `HEAD` ever held, including the
   orphaned commit and the reset that abandoned it:

   ```bash
   git reflog
   # ...
   # d9ae98c HEAD@{4}: commit: add upstream credentials for staging
   # 70355d0 HEAD@{3}: reset: moving to HEAD~1        <-- the smoking gun
   ```

2. **`git fsck`** reports the now-dangling object directly:

   ```bash
   git fsck --lost-found | grep "dangling commit"
   # dangling commit d9ae98c7c33e154cda10cfc1641e975b87d4d662
   ```

Either route gives you the commit hash. Read the file out of it:

```bash
git show d9ae98c:secrets.env
# or, via the reflog reference:
git show 'HEAD@{4}:secrets.env'
```

```
# DO NOT COMMIT
UPSTREAM_TOKEN=flag{wh1t3sp4ce_dns_m3m0ry_r3fl0g_full_ch41n_pwn3d}
```

**Output:** the final flag.

### The packaging subtlety (important, and part of the lesson)

Dangling commits and reflogs **do not survive `git clone` or `git push`** —
clone copies only reachable objects, and reflogs are strictly local.
If this repo were published as a normal GitHub repository, stage 4 would
be impossible: the flag object would be pruned server-side and no player
who cloned it would ever see it.

That's why the challenge ships the repo as a **tar.gz of the entire
`.git` directory** (reflogs intact), which players extract locally — not
as a live repo tree. This is itself a real, practical forensics lesson:
*the evidence you need is often in local-only git state that never leaves
the machine*, which is exactly why incident responders image `.git`
directories wholesale instead of re-cloning.

---

## Why the whole chain matters

Each stage maps to a real technique used by real attackers and
investigated by real responders:

- **Whitespace stego** — a genuine low-bandwidth exfil / watermarking
  channel; invisible to casual review, which is the whole point.
- **DNS tunneling** — one of the most common real-world exfiltration and
  C2 channels, precisely because DNS is almost never blocked outbound.
- **Memory carving** — credentials, keys, and URLs routinely live in
  process memory in plaintext long after they're "gone" from disk.
- **Git reflog leaks** — committing a secret and "removing" it is one of
  the most common credential-leak patterns on earth, and the reason tools
  like `trufflehog` and `git-secrets` exist. The reflog/dangling-object
  recovery here is exactly how those leaks are found (and exploited).

## Lessons for challenge design

Building a *chained* challenge is a different exercise from building four
separate ones: every stage's output has to be a clean, unambiguous
pointer into the next, with no dead ends and no unintended shortcuts. The
hardest part was stage 4's packaging — I only found the "dangling commits
don't survive clone/push" problem by actually testing the round trip
(zip, clone, extract) rather than assuming the repo would just work when
shipped. That's the kind of failure that would silently break the
challenge for every player, and it's invisible until you test the real
delivery path. Every stage in this writeup was verified by an independent
solver script (`solution/solve.py`) run against the shipped artifacts.
