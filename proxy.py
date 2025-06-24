from flask import Flask, Response, request
import requests

app = Flask(__name__)

@app.route("/watch/<path:url>")
def proxy(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url
        r = requests.get(url, headers=request.headers, stream=True, timeout=10)
        return Response(r.iter_content(chunk_size=1024), content_type=r.headers.get("Content-Type"))
    except Exception as e:
        return f"Proxy error: {e}", 500
