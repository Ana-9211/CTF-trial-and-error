# Related Secrets — Crypto (Medium)

> We send the same secret out twice, just... slightly offset. What's the harm?

## Description

Connect to our service. Every time you connect you'll get a **brand
new** RSA keypair and two ciphertexts: the flag encrypted once as-is,
and once shifted by a small, publicly-known constant (`delta`). Same
modulus, same exponent (`e = 3`), no padding.

We're not worried — you'd need to factor a 2048-bit modulus to break
this, and that's not happening.

**Goal:** recover the flag.

## Connecting

```bash
nc localhost 9999
```

or run the challenge locally:

```bash
cd challenge
docker compose up --build
```

## Files given to players

- `challenge/` — the full service source (this is exactly what's running
  on the scoring server; the flag itself is obviously swapped out)

## Flag format

`flag{...}`

---
*Category: Crypto · Difficulty: Medium · Points: 400*
