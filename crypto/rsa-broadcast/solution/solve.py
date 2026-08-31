#!/usr/bin/env python3
"""
Official solve script for the RSA Related-Message service.

Connects, parses the fresh (N, e, c1, c2, delta) the server hands out,
and recovers the flag via the Franklin-Reiter related-message attack -
no factoring of N required.

Usage:
    python3 solve.py TARGET_HOST TARGET_PORT
"""
import re
import socket
import sys

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9999


# ---- minimal polynomial arithmetic over Z_N (N need not be prime) ----

def poly_trim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def poly_sub(a, b, N):
    n = max(len(a), len(b))
    a = a + [0] * (n - len(a))
    b = b + [0] * (n - len(b))
    return poly_trim([(x - y) % N for x, y in zip(a, b)])


def poly_scalar_mul(a, s, N):
    return poly_trim([(c * s) % N for c in a])


def poly_shift(a, k):
    return [0] * k + a


def poly_mod(a, b, N):
    """a mod b over Z_N[x]. Requires leading coeff of b invertible mod N."""
    a = poly_trim(list(a))
    b = poly_trim(list(b))
    deg_b = len(b) - 1
    lead_b_inv = pow(b[-1], -1, N)
    while len(a) - 1 >= deg_b and not (len(a) == 1 and a[0] == 0):
        deg_a = len(a) - 1
        if deg_a < deg_b:
            break
        factor = (a[-1] * lead_b_inv) % N
        shift = deg_a - deg_b
        sub_term = poly_scalar_mul(poly_shift(b, shift), factor, N)
        a = poly_sub(a, sub_term, N)
        if a == [0]:
            break
    return poly_trim(a)


def poly_gcd(a, b, N):
    a = poly_trim(list(a))
    b = poly_trim(list(b))
    while not (len(b) == 1 and b[0] == 0):
        a, b = b, poly_mod(a, b, N)
    return a


def franklin_reiter(N: int, e: int, c1: int, c2: int, delta: int) -> int:
    assert e == 3, "this implementation targets e=3"
    # f1(x) = x^3 - c1
    f1 = [(-c1) % N, 0, 0, 1]
    # f2(x) = (x + delta)^3 - c2
    f2 = [(pow(delta, 3, N) - c2) % N, (3 * delta * delta) % N, (3 * delta) % N, 1]
    g = poly_gcd(f1, f2, N)
    if len(g) != 2:
        raise ValueError(f"expected a linear gcd factor, got degree {len(g)-1}")
    a0, a1 = g
    m1 = (-a0 * pow(a1, -1, N)) % N
    return m1


def parse_server_output(data: str):
    N = int(re.search(r"N\s*=\s*(0x[0-9a-fA-F]+)", data).group(1), 16)
    e = int(re.search(r"e\s*=\s*(\d+)", data).group(1))
    c1 = int(re.search(r"c1\s*=\s*(0x[0-9a-fA-F]+)", data).group(1), 16)
    c2 = int(re.search(r"c2\s*=\s*(0x[0-9a-fA-F]+)", data).group(1), 16)
    delta = int(re.search(r"delta\s*=\s*(\d+)", data).group(1))
    return N, e, c1, c2, delta


def solve(host: str, port: int) -> str | None:
    with socket.create_connection((host, port), timeout=10) as sock:
        chunks = []
        sock.settimeout(5)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        except socket.timeout:
            pass
        data = b"".join(chunks).decode()

    print(data)
    N, e, c1, c2, delta = parse_server_output(data)
    print(f"[*] Parsed N ({N.bit_length()} bits), e={e}, delta={delta}")

    m1 = franklin_reiter(N, e, c1, c2, delta)
    flag_bytes = m1.to_bytes((m1.bit_length() + 7) // 8, "big")
    try:
        flag = flag_bytes.decode()
    except UnicodeDecodeError:
        flag = repr(flag_bytes)

    print(f"[+] FLAG: {flag}")
    return flag


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    solve(host, port)
