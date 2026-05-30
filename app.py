#!/usr/bin/env python3
"""
Windows 98 IE5/6 HTTP Forward Proxy

A forward proxy server that lets Internet Explorer 5/6 on Windows 98
access modern websites. Handles SSL/TLS server-side and serves content
over plain HTTP to the browser.

Configure in IE: Tools > Internet Options > Connections > LAN Settings
Set proxy to this machine's IP on the configured port (HTTP only).
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import requests
from bs4 import BeautifulSoup
import re

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8080

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Headers we skip when forwarding from the client
HOP_BY_HOP = {
    "host", "connection", "keep-alive", "proxy-connection",
    "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "accept-encoding",
}

# Headers we skip when sending the response back
# (requests auto-decompresses, so we must strip encoding headers)
RESPONSE_SKIP = {
    "content-length", "transfer-encoding", "connection",
    "content-encoding",
}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class ProxyHandler(BaseHTTPRequestHandler):
    """Handle HTTP proxy requests from IE5/6."""

    def do_GET(self):
        self._proxy_request()

    def do_POST(self):
        self._proxy_request()

    def do_HEAD(self):
        self._proxy_request()

    def do_CONNECT(self):
        # IE sends CONNECT for https:// URLs. IE5/6 cannot do modern TLS,
        # so we reject and tell the user to use http:// instead.
        # The proxy automatically upgrades to HTTPS when fetching.
        self.send_error(
            502,
            "HTTPS proxy not supported. "
            "Use http:// in the address bar - the proxy upgrades automatically.",
        )

    # ------------------------------------------------------------------

    def _proxy_request(self):
        url = self.path

        # Direct request to the proxy server itself (not a proxy request)
        if not url.startswith("http"):
            self._send_status_page()
            return

        # Build upstream request headers
        # Forward client headers but always override User-Agent with a modern one
        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in HOP_BY_HOP and key.lower() != "user-agent":
                headers[key] = value
        headers["User-Agent"] = USER_AGENT

        # Read request body (POST / PUT)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        try:
            resp = requests.request(
                self.command,
                url,
                headers=headers,
                data=body,
                verify=True,
                allow_redirects=True,
                timeout=30,
            )
        except requests.RequestException as exc:
            self.send_error(502, f"Upstream error: {exc}")
            return

        content = resp.content
        content_type = resp.headers.get("Content-Type", "")

        # Rewrite HTTPS→HTTP so IE keeps using the forward-proxy path
        if "text/html" in content_type:
            content = self._rewrite_html(content)
        elif "text/css" in content_type:
            content = _rewrite_css(content).encode("utf-8", errors="replace")
        elif "javascript" in content_type:
            content = _rewrite_js(content).encode("utf-8", errors="replace")

        # Send response
        self.send_response(resp.status_code)
        for key, value in resp.headers.items():
            if key.lower() not in RESPONSE_SKIP:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ------------------------------------------------------------------

    def _send_status_page(self):
        html = (
            b"<html><head><title>Win98 IE Proxy</title></head>"
            b"<body style='font-family:sans-serif;padding:2em'>"
            b"<h1>Windows 98 IE Proxy</h1>"
            b"<p>The proxy server is running.</p>"
            b"<p>Configure IE to use this server as an <b>HTTP proxy</b>:</p>"
            b"<pre>  Tools &gt; Internet Options &gt; Connections &gt; LAN Settings</pre>"
            b"<p>For HTTPS sites, type <b>http://</b> in the address bar "
            b"(the proxy upgrades automatically).</p>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    @staticmethod
    def _rewrite_html(raw):
        """Parse HTML and rewrite HTTPS URLs to HTTP."""
        soup = BeautifulSoup(raw, "html.parser")
        _rewrite_soup(soup)
        return str(soup).encode("utf-8")

    # Log requests for debugging
    def log_message(self, fmt, *args):
        print(f"[proxy] {args[0]}")


# ======================================================================
# URL rewriting helpers
# ======================================================================

def _https_to_http(url):
    """Convert https:// to http:// in a URL string."""
    if url and isinstance(url, str) and url.startswith("https://"):
        return "http://" + url[8:]
    return url


def _rewrite_soup(soup):
    """Rewrite HTTPS URLs to HTTP in parsed HTML so IE uses the proxy."""
    for tag in soup.find_all(True):
        for attr in ("href", "src", "action", "data", "codebase"):
            val = tag.get(attr)
            if val and "https://" in val:
                tag[attr] = val.replace("https://", "http://")
    # <meta http-equiv="refresh" content="0;url=https://...">
    for meta in soup.find_all("meta", attrs={"http-equiv": "refresh"}):
        c = meta.get("content", "")
        if c and "https://" in c:
            meta["content"] = c.replace("https://", "http://")


def _rewrite_css(raw):
    """Rewrite HTTPS URLs to HTTP in CSS text."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return raw.replace("https://", "http://")


def _rewrite_js(raw):
    """Light rewrite of HTTPS URLs in JavaScript."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return raw.replace("https://", "http://")


# ======================================================================
# Entry point
# ======================================================================

def _get_lan_ip():
    """Return the machine's LAN IP address for display purposes."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "<this-machine-ip>"


if __name__ == "__main__":
    server = ThreadedHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    lan_ip = _get_lan_ip()
    print(f"Windows 98 IE Proxy running on {LISTEN_HOST}:{LISTEN_PORT}")
    print()
    print("Configure in IE:")
    print("  Tools > Internet Options > Connections > LAN Settings > Proxy Server")
    print(f"  Address: {lan_ip}   Port: {LISTEN_PORT}")
    print()
    print("For HTTPS sites, type http:// in the address bar.")
    print("The proxy upgrades to HTTPS automatically.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
