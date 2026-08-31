"""Builds stage-3 aurora.dmp: a lightweight synthetic memory blob.

Not a real Volatility-format image (by design - see writeup); it's a
realistic chunk of process memory: mostly binary noise and plausible
in-memory string artifacts, with the stage-4 pointer embedded near the
AURORA_KEYBLOCK marker that stage 2 told the player to search for.

Solvable with: strings | grep, or binwalk, or a hex editor search.
"""
import os
import random

MARKER = b"AURORA_KEYBLOCK"

# stage-4 pointer: a local bare git repo the player then examines.
# In deployment this is the path to the repo bundle shipped alongside.
KEYBLOCK = (
    b"AURORA_KEYBLOCK\n"
    b"repo=aurora-config.git\n"
    b"note=creds rotated; old commit was dropped from main\n"
    b"hint=the secret was committed then removed - check where git keeps\n"
    b"     references that survive a delete (reflog / dangling objects)\n"
    b"AURORA_KEYBLOCK_END\n"
)

def plausible_strings():
    """Realistic-looking in-memory string litter."""
    return [
        b"/usr/lib/x86_64-linux-gnu/libc.so.6",
        b"LANG=en_US.UTF-8",
        b"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        b"GET /health HTTP/1.1",
        b"Host: 127.0.0.1:8080",
        b"aurora.shipper.connection.established",
        b"upstream=ingest.internal.lab:6514",
        b"batch flushed seq=48213 bytes=1048576",
        b"SSL_connect: handshake ok",
        b"rotator: unlinked /var/log/aurora/buf.000017",
        b"ld-linux-x86-64.so.2",
        b"malloc(): corrupted top size",
        b"__libc_start_main",
    ]

def main():
    rng = random.Random(1337)
    size = 512 * 1024  # 512 KB - big enough to feel real, small enough to ship
    buf = bytearray(rng.getrandbits(8) for _ in range(size))

    # scatter plausible strings through the "memory"
    strings = plausible_strings()
    for s in strings:
        for _ in range(rng.randint(2, 5)):
            pos = rng.randint(0, size - len(s) - 1)
            buf[pos:pos+len(s)] = s

    # embed the keyblock at a pseudo-random offset in the second half
    kb_pos = rng.randint(size // 2, size - len(KEYBLOCK) - 1)
    buf[kb_pos:kb_pos+len(KEYBLOCK)] = KEYBLOCK

    with open("aurora.dmp", "wb") as f:
        f.write(buf)

    print(f"dump size     : {size} bytes")
    print(f"keyblock at   : offset {kb_pos}")
    print(f"marker        : {MARKER.decode()}")

if __name__ == "__main__":
    main()
