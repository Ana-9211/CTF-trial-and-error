"""
Simulated cloud instance metadata service.
In a real cloud environment this listens on 169.254.169.254 and is only
reachable from inside the VM/container itself - never from the public
internet. That's exactly why SSRF is dangerous: it lets an outside
attacker make the *server* ask this question on their behalf.
"""
from flask import Flask, jsonify

app = Flask(__name__)

FLAG = "flag{ssrf_pdf_render_naive_blocklist_bypass}"


@app.route("/latest/meta-data/")
def meta_root():
    return "iam/\nhostname\ninstance-id\n"


@app.route("/latest/meta-data/iam/security-credentials/")
def iam_root():
    return "internal-service-role\n"


@app.route("/latest/meta-data/iam/security-credentials/internal-service-role")
def creds():
    return jsonify({
        "AccessKeyId": "AKIAEXAMPLESSRFDEMO",
        "SecretAccessKey": FLAG,
        "Token": "example-session-token",
        "Expiration": "2099-01-01T00:00:00Z",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
