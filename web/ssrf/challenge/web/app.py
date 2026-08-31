"""
DocuRender - "paste a URL, get a PDF" service.

Internal note (not shipped to players): the blocklist below checks the
*hostname string* pulled out of the URL. It does not check what IP that
hostname actually resolves to, and it doesn't normalize numeric IP
formats before comparing. That's the bug.
"""
from flask import Flask, request, send_file, jsonify
import requests
from fpdf import FPDF
from urllib.parse import urlparse
import io

app = Flask(__name__)

BLOCKLIST = ["localhost", "127.0.0.1", "169.254.169.254", "0.0.0.0", "::1"]


def is_blocked(url: str) -> bool:
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except Exception:
        return True
    return any(bad in hostname for bad in BLOCKLIST)


@app.route("/")
def index():
    return """
    <h2>DocuRender</h2>
    <p>Paste a public URL and we'll render it to a PDF for you.</p>
    <form action="/render" method="post">
      <input name="url" placeholder="https://example.com" size="50">
      <button type="submit">Render PDF</button>
    </form>
    """


@app.route("/render", methods=["POST"])
def render():
    url = request.form.get("url", "")

    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "only http(s) URLs are allowed"}), 400

    if is_blocked(url):
        return jsonify({"error": "that host is not allowed"}), 403

    try:
        resp = requests.get(url, timeout=5)
    except Exception as e:
        return jsonify({"error": f"could not fetch url: {e}"}), 502

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    text = resp.text[:6000]
    for line in text.splitlines():
        safe_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe_line)

    buf = io.BytesIO(bytes(pdf.output()))
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name="rendered.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
