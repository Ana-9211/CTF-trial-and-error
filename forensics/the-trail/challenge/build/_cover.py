# Generates a long, realistic internal-engineering-doc cover text with plenty
# of eligible prose lines. Sections read like a real maintained README so the
# whitespace stego has believable cover.
SECTIONS = [
    ("# Project Aurora", [
        "Aurora is our internal log aggregation and shipping service.",
        "It gathers application logs from across the fleet and forwards",
        "them to the central analytics store for retention and search.",
        "The design has always aimed to stay small and dependency free.",
        "It has run in production for several years with little churn.",
    ]),
    ("## Overview", [
        "The service is built around three cooperating components, each",
        "owning one clear responsibility. Keeping the boundaries sharp",
        "makes the system easy to reason about during incidents, which",
        "is exactly when clarity matters most to the on call engineer.",
        "Everything below the transport layer is deliberately boring,",
        "because boring code is the code that pages you least often.",
        "The three parts are the collector, the shipper, and the rotator.",
        "They communicate through a small on disk queue on each host.",
    ]),
    ("## The collector", [
        "The collector discovers log sources on a host at startup and",
        "then watches for new ones on a slow rescan interval afterwards.",
        "It watches a configured set of directories and tails the files",
        "that match the include patterns while honouring the excludes.",
        "As new lines arrive they are grouped into batches to cut down",
        "on syscalls and to amortise the cost of upstream delivery.",
        "Batching is bounded by both time and size, so even a quiet host",
        "ships on a predictable cadence instead of hoarding its lines",
        "until some large byte threshold is eventually crossed at last.",
        "Each record is stamped with a monotonic per host identifier.",
        "That identifier is what downstream consumers use to deduplicate.",
    ]),
    ("## The shipper", [
        "The shipper takes completed batches and delivers them upstream.",
        "It holds a persistent connection to the central ingest endpoint",
        "and manages backpressure by spilling to local disk whenever the",
        "upstream is slow, saturated, or briefly unreachable for a while.",
        "On reconnect it drains the local buffer strictly in order, so",
        "downstream consumers never observe records out of their sequence.",
        "Delivery is at least once by design, never exactly once, and so",
        "consumers must dedupe on the record identifier when they need it.",
        "The connection is health checked with a lightweight ping frame.",
        "A missed ping trips a fast reconnect rather than a slow timeout.",
    ]),
    ("## The rotator", [
        "The rotator manages local retention independently on every host.",
        "Once a batch has been acknowledged by the upstream ingest it is",
        "marked eligible for cleanup, subject to a minimum local window.",
        "That retention window exists purely for local debugging comfort.",
        "Rotation runs on a timer and is careful never to remove a file",
        "that the collector still holds an open handle against right then.",
        "This avoids the classic deleted but still growing file problem",
        "that quietly wastes disk on long lived hosts for days on end.",
        "Freed space is reported back through the health endpoint counters.",
    ]),
    ("## Configuration", [
        "All configuration is supplied through environment variables, so",
        "the very same image can be promoted unchanged across every tier.",
        "There is no configuration file to drift out of sync over time,",
        "and no secrets are ever baked into the build image at any point.",
        "The full list of supported keys, their types, and their default",
        "values lives right beside the code for quick and easy reference.",
        "Operators usually override only a small handful of keys in real",
        "deployments, leaving the rest of the tuning at its tested values.",
        "The upstream endpoint and its credentials are the two settings",
        "that reliably change between one environment and the next one.",
        "Most tuning parameters have defaults that have held up under our",
        "production load and are rarely worth touching without good reason.",
    ]),
    ("## Operations", [
        "Health is exposed on a local endpoint returning a small summary",
        "of queue depth, last successful ship time, and buffer occupancy.",
        "Alerting is wired primarily to the last successful ship time,",
        "since a stalled shipper is the failure that actually loses data.",
        "Everything else tends to heal itself within a retry cycle or two",
        "and rarely needs a human to intervene before the next poll runs.",
        "Deployments are rolling and need no explicit draining step first,",
        "because the disk buffer covers the gap while a replacement starts.",
        "Routine restarts are therefore genuinely uneventful in practice,",
        "which is the property you want from shared infrastructure code.",
        "Capacity planning is driven off the buffer occupancy trend line.",
        "A rising floor on that trend is the earliest sign of trouble.",
    ]),
    ("## Troubleshooting", [
        "If logs stop arriving the first check is the ship time metric.",
        "A recent ship time with a growing queue points at the collector.",
        "An old ship time with a full buffer points instead at the link.",
        "The buffer is safe to inspect directly while the service runs.",
        "It is an append only log of framed batches with a simple header.",
        "A corrupt header at the tail is truncated on the next start up.",
        "Anything before the corruption point is preserved and delivered.",
        "When in doubt a restart is safe and never drops acknowledged data.",
    ]),
    ("## Performance", [
        "A single instance comfortably handles the log volume of one host,",
        "including the noisy ones that emit bursts during batch job runs.",
        "Memory use is bounded by the batch size and the connection buffers,",
        "so it stays flat regardless of how long the process has been up.",
        "Cpu use is dominated by framing and is negligible at steady state.",
        "The disk buffer is the only resource that grows under an outage,",
        "and its ceiling is configurable per host based on available space.",
        "When the ceiling is reached the oldest unshipped batch is dropped,",
        "and that drop is counted and surfaced loudly on the health summary.",
    ]),
    ("## History", [
        "Aurora replaced an older shell based shipper that predated it,",
        "which had grown fragile and impossible to reason about safely.",
        "The rewrite deliberately kept the on disk format compatible so",
        "that a migration could proceed host by host without a big flag.",
        "Several sharp edges from that era survive as defensive checks.",
        "Those checks look paranoid until the one night they save you.",
        "The commit history from the migration was later squashed down,",
        "and some early references were archived out of the repository.",
    ]),
    ("## Data model", [
        "A record is a timestamp, a source label, and an opaque payload.",
        "The service never parses the payload and treats it as raw bytes.",
        "This keeps the shipper agnostic to whatever the application logs,",
        "whether that is plain text, structured json, or a binary format.",
        "The source label is derived from the originating file path and",
        "is stable across rotations of that same underlying log file name.",
        "Consumers group by the source label to reconstruct a host view.",
        "The timestamp is capture time on the host, not application time,",
        "which matters when a host clock has drifted from real wall time.",
        "A separate field carries the application supplied time when present.",
    ]),
    ("## Security", [
        "The service runs as an unprivileged user on every deployed host.",
        "It reads only the log directories it is explicitly configured for.",
        "Credentials for the upstream are injected at runtime, never stored.",
        "The local buffer is readable only by the service account itself.",
        "No inbound network ports are opened other than the health check.",
        "That health endpoint binds to loopback and is never exposed wider.",
        "All upstream traffic is mutually authenticated over a modern cipher.",
        "Rotated buffers are unlinked, not merely truncated, once delivered.",
    ]),
    ("## Testing", [
        "The unit suite covers framing, batching, and the retention timer.",
        "An integration harness spins up a fake upstream and a live shipper.",
        "It asserts ordering guarantees survive an induced reconnect storm.",
        "A soak test runs the whole thing for hours under synthetic load.",
        "The soak test is what actually catches the slow buffer leaks early.",
        "Coverage is tracked but never treated as a target in its own right.",
    ]),
    ("## Status", [
        "Aurora is in long term maintenance mode at this stage of life.",
        "No new features are planned or particularly wanted at this time,",
        "and the roadmap is limited to security patches as they are needed.",
        "The service does its single job well and we leave it be otherwise.",
    ]),
    ("## Notes", [
        "Older build notes, migration records, and assorted internal",
        "references have been archived out of this document over time to",
        "keep it readable for whoever inherits it next after the authors.",
        "The platform team retains that archive and can grant access on",
        "request when some historical detail is genuinely needed later.",
    ]),
    ("## Contributing", [
        "Changes are small and reviewed by at least one platform engineer.",
        "The bar for new dependencies is deliberately and famously high.",
        "Most proposed features are politely declined as out of scope now.",
        "Bug fixes with a regression test are always welcome regardless.",
        "The style is enforced by the formatter so reviews stay on logic.",
        "Documentation changes count as changes and follow the same path.",
        "A changelog entry is expected for anything a user could notice.",
        "Release tags are cut by hand after the soak test comes back clean.",
        "There is no automatic release on merge and that is intentional.",
        "The maintainers prefer a deliberate human in that particular loop.",
    ]),
    ("## License", [
        "Internal use only. This document and its associated source are",
        "not approved for redistribution outside the organisation at all.",
    ]),
]

def build_cover() -> str:
    out = []
    for header, body in SECTIONS:
        out.append(header)
        out.append("")
        for line in body:
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip() + "\n"

if __name__ == "__main__":
    cover = build_cover()
    eligible = sum(
        1 for ln in cover.split("\n")
        if ln.strip() and not ln.strip().startswith("#")
        and not ln.strip().startswith(("- ", "* "))
    )
    print(f"total lines: {len(cover.splitlines())}")
    print(f"eligible prose lines: {eligible}")
