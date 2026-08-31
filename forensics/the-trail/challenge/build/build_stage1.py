"""Builds stage-1 README.md with a hidden message in TRAILING whitespace.

Encoding (classic whitespace stego, stegsnow-style):
  - one hidden BIT per eligible line, carried as a single trailing char
  - trailing SPACE = bit 0, trailing TAB = bit 1
  - eligible line = non-empty prose line (not blank, not a markdown
    heading, not a list marker)
  - read the eligible lines top to bottom, 8 bits per character, MSB first

Payload: the exfil hostname the player pivots to in stage 2 (the DNS pcap).
"""
from _cover import build_cover

HIDDEN = "exfil.notreal.lab"


def is_eligible(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):
        return False
    if s.startswith("- ") or s.startswith("* "):
        return False
    return True


def main():
    bits = "".join(format(ord(c), "08b") for c in HIDDEN)
    lines = build_cover().split("\n")

    eligible_count = sum(1 for ln in lines if is_eligible(ln))
    if eligible_count < len(bits):
        raise SystemExit(
            f"cover text too short: need {len(bits)} eligible lines, have {eligible_count}"
        )

    out = []
    bi = 0
    for ln in lines:
        if is_eligible(ln) and bi < len(bits):
            ln = ln.rstrip()
            ln += " " if bits[bi] == "0" else "\t"
            bi += 1
        out.append(ln)

    with open("AURORA_README.md", "w") as f:
        f.write("\n".join(out))

    print(f"hidden payload : {HIDDEN!r}")
    print(f"bits encoded   : {len(bits)}")
    print(f"eligible lines : {eligible_count} (used {bi})")


if __name__ == "__main__":
    main()
