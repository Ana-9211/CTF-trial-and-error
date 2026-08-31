# SSRF / DocuRender — Web (Medium)

> Paste a URL, get a PDF. What could go wrong?

## Description

Our internal team built **DocuRender**, a tiny service that turns any web
page into a clean, printable PDF. Just give it a URL.

We know better than to let it fetch anything from our internal network
though — we've blocked the obvious hosts (`localhost`, `127.0.0.1`,
`169.254.169.254`, etc.). Should be safe.

**Goal:** retrieve the flag.

## Running it

```bash
cd challenge
docker compose up --build
```

The renderer will be available at `http://localhost:5000`.

## Files given to players

- `challenge/` — everything needed to run the service locally (this is
  exactly what's deployed on the scoring server)

## Flag format

`flag{...}`

---
*Category: Web · Difficulty: Medium · Points: 350*
