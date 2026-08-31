"""
RSA "Related Message" service.

Every connection gets a FRESH 2048-bit RSA modulus (e=3) and encrypts the
flag twice: once as-is, once shifted by a small known public constant
(delta). Since a fresh keypair is generated per connection, there's no
point hardcoding numbers from one session - the intended solve has to be
a real, automated attack.

Internal note (not shipped to players): this is intentionally textbook
RSA - no OAEP padding. That's the whole point: with two ciphertexts of
two *known-related* plaintexts under the same (N, e=3), the Franklin-
Reiter attack recovers the plaintext without ever factoring N.
"""
import socketserver
import threading
from Crypto.Util.number import getPrime

with open("flag.txt", "rb") as f:
    FLAG = f.read().strip()

E = 3
DELTA = 1337  # public, known to the player - the "related" part of the message


def gen_keypair(bits=2048):
    p = getPrime(bits // 2)
    q = getPrime(bits // 2)
    return p * q


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        try:
            N = gen_keypair()

            m1 = int.from_bytes(FLAG, "big")
            m2 = m1 + DELTA
            c1 = pow(m1, E, N)
            c2 = pow(m2, E, N)

            banner = (
                "=== RSA Related-Message Service ===\n"
                "Two copies of the same secret get sent out, related by a\n"
                "known public offset. Good luck.\n\n"
                f"N     = {hex(N)}\n"
                f"e     = {E}\n"
                f"c1    = {hex(c1)}\n"
                f"c2    = {hex(c2)}\n"
                f"delta = {DELTA}   (m2 = m1 + delta)\n"
            )
            self.request.sendall(banner.encode())
        except Exception as exc:
            try:
                self.request.sendall(f"error: {exc}\n".encode())
            except Exception:
                pass


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 9999
    server = ThreadingServer((HOST, PORT), Handler)
    print(f"[*] listening on {HOST}:{PORT}")
    server.serve_forever()
