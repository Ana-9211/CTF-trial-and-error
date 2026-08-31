# Official Writeup — Related Secrets (RSA / Franklin-Reiter)

**Category:** Crypto &nbsp;|&nbsp; **Difficulty:** Medium &nbsp;|&nbsp;
**Flag:** `flag{fr4nkl1n_re1t3r_r3lat3d_m3ssag3_att4ck_n0_f4ct0r1ng_n33d3d}`

## 1. Vulnerability class

**Textbook RSA (no padding) + related-message reuse.** The service
encrypts two messages that are *linearly related* — `m` and `m + delta`
for a known public constant `delta` — under the same modulus and public
exponent, with `e = 3` and no OAEP/PKCS#1 padding. This is exploitable
via the **Franklin-Reiter related-message attack**, which recovers the
plaintext without ever factoring `N`.

This is a different (and less commonly built) flaw than the more
famous **Håstad broadcast attack**, which needs `e` different moduli
encrypting the *identical* message. Here there's only ever one modulus —
the vulnerability is about the relationship *between two messages*, not
about reuse across recipients.

## 2. Why this is attackable at all

For textbook RSA, `c = m^e mod N`. With `e = 3` and no padding, this is
a bare cubic. Consider two ciphertexts under the *same* `N`:

```
c1 = m^3 mod N
c2 = (m + delta)^3 mod N
```

Define two polynomials over the ring `Z_N[x]`:

```
f1(x) = x^3 - c1
f2(x) = (x + delta)^3 - c2
```

Both polynomials have `x = m` as a root (by construction — plug `m` back
in and both vanish). Assuming `m` is their *only* common root (true with
overwhelming probability for essentially any real message), their
**GCD** in `Z_N[x]` is the linear polynomial `(x - m)` — computed via the
polynomial Euclidean algorithm, exactly like `gcd()` for integers, just
with polynomial long division instead.

The key insight — and the reason this doesn't need factoring `N` — is
that polynomial division only requires **inverting the leading
coefficient of the divisor modulo N**, not full arithmetic over a field.
For a random 2048-bit RSA modulus, any given leading coefficient
produced during the algorithm is invertible mod `N` with probability
`1 - negligible` (the only way it isn't is if it happens to share a
factor with `N`, which would itself immediately break the modulus). So
the Euclidean algorithm runs to completion over `Z_N[x]` even though
`Z_N` is not a field.

## 3. The attack, concretely

Expand `f2(x) = (x + delta)^3 - c2`:

```
f2(x) = x^3 + 3*delta*x^2 + 3*delta^2*x + (delta^3 - c2)
```

Represent both as coefficient lists (constant term first):

```
f1 = [-c1 mod N, 0, 0, 1]
f2 = [(delta^3 - c2) mod N, 3*delta^2 mod N, 3*delta mod N, 1]
```

Run the polynomial Euclidean algorithm:

```
while f2 != 0:
    f1, f2 = f2, (f1 mod f2)
gcd = f1
```

Polynomial `mod` here means long division remainder, where each division
step multiplies by `inverse(leading_coeff(divisor), N)` — the only place
modular inversion is needed.

The result reduces to a linear polynomial `a1*x + a0`. Since it's a
scalar multiple of `(x - m)`:

```
m = (-a0 * inverse(a1, N)) mod N
```

Convert `m` back to bytes and you have the flag.

## 4. Exploiting the live service

Because the service hands out a **fresh 2048-bit modulus every
connection**, there's nothing to precompute or hardcode — the solve has
to be a real, working implementation run against whatever `(N, c1, c2)`
you're given at connect time. That was a deliberate design choice: a
static-file version of this challenge can be solved once by hand with
help from a CAS; a live service forces you to actually finish and debug
a working script.

```bash
nc localhost 9999
# === RSA Related-Message Service ===
# N     = 0x86dee0...
# e     = 3
# c1    = 0x10652c...
# c2    = 0x10652c...
# delta = 1337
```

Feed those four values into the Franklin-Reiter routine above and
recover `m`. `solution/solve.py` automates the full round trip —
connect, parse, attack, decode — and completes in under 2 seconds
including the server's own 2048-bit key generation.

## 5. Design rationale — why e=3 and why 2048-bit

- **`e = 3`** keeps the polynomial GCD at degree 3, which is fast and
  easy to reason about by hand — appropriate for a "medium" slot. Larger
  `e` values are attackable too (the general related-message attack
  generalizes), but the polynomial arithmetic gets messier for a
  writeup without adding much conceptual depth.
- **2048-bit modulus** was chosen specifically so that **factoring `N`
  directly is not a viable unintended solution path** — the attack's
  cost doesn't depend on modulus size at all (it's a handful of
  polynomial operations on numbers with a couple thousand bits, entirely
  independent of factoring difficulty), so making `N` cryptographically
  unfactorable costs nothing in server-side performance while ruling out
  "just brute force it" as an escape hatch.
- **Fresh keys per connection** turns this from "recognize the attack"
  into "have working tooling for the attack," which is a meaningfully
  higher bar and more representative of what real crypto-review tooling
  looks like.

## 6. Why this matters (real-world mapping)

Related-message attacks are the reason serious crypto libraries never
implement raw textbook RSA and always mandate padding schemes like
OAEP. Concretely:

- OAEP padding randomizes each encryption independently, so `m` and
  `m + delta` no longer have any algebraic relationship after padding —
  this single design choice kills the entire attack class.
- Historically, protocols that "cleverly" encrypt structurally related
  values (sequence numbers, incrementing counters, near-duplicate
  messages) under raw RSA have been broken exactly this way — it's a
  recurring pattern in academic cryptanalysis of custom/legacy protocols
  that predate or ignore padding standards.
- The broader lesson: **RSA's algebraic structure is not incidental —
  it's multiplicatively homomorphic, and anything that lets an attacker
  relate two plaintexts algebraically (not just "reuse the same key")
  can potentially be turned into a solvable system.**

## 7. Remediation

1. **Always use OAEP** (`RSAES-OAEP`) for RSA encryption — never raw/
   textbook RSA in production. This alone prevents this entire attack
   class, since padding destroys the algebraic relationship between
   plaintexts.
2. **Never encrypt related plaintexts** under the same key with a
   deterministic scheme, even with reasonable-looking exponents.
3. Prefer **hybrid encryption** (RSA to wrap a random symmetric key,
   then AEAD for the actual payload) over direct RSA encryption of
   application data in the first place.

## 8. Lessons for challenge design

The interesting part of building this wasn't wiring up sockets — it was
implementing polynomial GCD **over a non-field ring** correctly, which
forces you to actually understand *why* the attack works (leading-
coefficient invertibility) rather than just knowing "Franklin-Reiter
exists." Testing it against a live, freshly-keyed server rather than a
canned static example was the only way to be confident the intended
solve path is real and reliable, not just correct on one lucky
plaintext/modulus pair.
