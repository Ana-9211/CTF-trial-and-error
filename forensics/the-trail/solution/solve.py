#!/usr/bin/env python3
"""
Official full-chain solver for "The Trail" (forensics).

Runs all four stages end to end:
  1. whitespace stego in AURORA_README.md  -> exfil hostname
  2. DNS-tunnel capture.pcap                -> memory dump + marker pointer
  3. aurora.dmp memory blob                 -> git repo + reflog hint
  4. git reflog / dangling commit           -> final flag

Usage:
    python3 solve.py /path/to/challenge/files
"""
import base64
import os
import subprocess
import sys
import tarfile
import tempfile


def stage1_whitespace(files_dir: str) -> str:
    path = os.path.join(files_dir, "AURORA_README.md")
    with open(path) as f:
        lines = f.read().split("\n")

    def eligible(line):
        s = line.strip()
        return bool(s) and not s.startswith("#") and not s.startswith(("- ", "* "))

    bits = ""
    for line in lines:
        if not eligible(line):
            continue
        stripped = line.rstrip()
        trailing = line[len(stripped):]
        if not trailing:
            continue
        bits += "0" if trailing[-1] == " " else "1"

    chars = [chr(int(bits[i:i+8], 2)) for i in range(0, len(bits) - 7, 8)]
    host = "".join(chars)
    print(f"[stage 1] recovered exfil host: {host}")
    return host


def stage2_dns(files_dir: str, tunnel_domain: str) -> str:
    from scapy.all import rdpcap, DNSQR
    pkts = rdpcap(os.path.join(files_dir, "capture.pcap"))
    seen = {}
    for p in pkts:
        if not p.haslayer(DNSQR):
            continue
        qname = p[DNSQR].qname.decode().rstrip(".")
        if not qname.endswith(tunnel_domain):
            continue
        labels = qname.split(".")
        if len(labels) < 5:
            continue
        try:
            seq = int(labels[1])
        except ValueError:
            continue
        seen[seq] = labels[0]

    b32 = "".join(seen[k] for k in sorted(seen))
    b32 += "=" * ((-len(b32)) % 8)
    payload = base64.b32decode(b32).decode()
    print(f"[stage 2] DNS-tunnel payload: {payload}")
    return payload


def stage3_memory(files_dir: str, marker: str) -> str:
    path = os.path.join(files_dir, "aurora.dmp")
    with open(path, "rb") as f:
        data = f.read()
    idx = data.find(marker.encode())
    if idx == -1:
        raise RuntimeError(f"marker {marker!r} not found in memory dump")
    block = data[idx:idx + 400].split(b"AURORA_KEYBLOCK_END")[0].decode(errors="replace")
    print("[stage 3] memory keyblock:")
    for line in block.splitlines():
        print(f"          {line}")
    return block


def stage4_git(files_dir: str) -> str:
    tarpath = os.path.join(files_dir, "aurora-config-repo.tar.gz")
    tmp = tempfile.mkdtemp()
    with tarfile.open(tarpath) as t:
        t.extractall(tmp)
    repo = os.path.join(tmp, "aurora-config")

    # find the orphaned commit via reflog
    reflog = subprocess.run(["git", "reflog"], cwd=repo,
                            capture_output=True, text=True).stdout
    target = None
    for line in reflog.splitlines():
        if "credential" in line.lower():
            target = line.split()[0]
            break
    if not target:
        # fallback: fsck for dangling commit
        fsck = subprocess.run(["git", "fsck", "--lost-found"], cwd=repo,
                              capture_output=True, text=True).stdout
        for line in fsck.splitlines():
            if "dangling commit" in line:
                target = line.split()[-1]
                break
    if not target:
        raise RuntimeError("could not locate the orphaned commit")

    show = subprocess.run(["git", "show", f"{target}:secrets.env"], cwd=repo,
                          capture_output=True, text=True).stdout
    for line in show.splitlines():
        if "flag{" in line:
            flag = line.split("=", 1)[1].strip()
            print(f"[stage 4] recovered from dangling commit {target[:8]}")
            print(f"\n[+] FLAG: {flag}")
            return flag
    raise RuntimeError("flag not found in recovered commit")


def main():
    files_dir = sys.argv[1] if len(sys.argv) > 1 else "challenge/files"

    host = stage1_whitespace(files_dir)
    payload2 = stage2_dns(files_dir, host)
    # parse "memory:aurora.dmp marker:AURORA_KEYBLOCK"
    marker = dict(kv.split(":", 1) for kv in payload2.split())["marker"]
    stage3_memory(files_dir, marker)
    stage4_git(files_dir)


if __name__ == "__main__":
    main()
