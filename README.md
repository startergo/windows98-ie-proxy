# Windows 98 IE5/6 HTTP Proxy

A forward HTTP proxy server that enables Internet Explorer 5/6 on Windows 98
to access modern websites. It handles SSL/TLS on the server side and serves
content over plain HTTP to the browser, bypassing the encryption limitations
of older browsers.

## Features

- **Forward HTTP Proxy:** Configure directly in IE's proxy settings — no special URL format needed.
- **SSL/TLS Handling:** Fetches HTTPS sites transparently and serves them over HTTP.
- **Content Rewriting:** Rewrites `https://` URLs to `http://` in HTML, CSS, and JavaScript so IE stays on the proxy path.
- **Multi-threaded:** Handles concurrent requests from the browser.
- **User-Agent Spoofing:** Sends a modern User-Agent so upstream servers return usable content.

## Requirements

- Python 3.6+
- requests
- BeautifulSoup4

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/startergo/windows98-ie-proxy.git
   ```
2. Navigate to the project directory:
   ```
   cd windows98-ie-proxy
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the proxy server:

```
python app.py
```

The server listens on `0.0.0.0:8080` by default. You can change `LISTEN_PORT`
in `app.py` or pass a custom port via the `PORT` environment variable.

### Configuring Internet Explorer

1. Open **Tools → Internet Options → Connections → LAN Settings**.
2. Check **Use a proxy server**.
3. Set **Address** to the IP address of the machine running the proxy.
4. Set **Port** to `8080` (or whichever port you configured).
5. Click **Advanced** and ensure the proxy is set for **HTTP** only.
   Leave the **Secure** (HTTPS) field empty.
6. Click OK to save.

### Browsing

- Type URLs normally in the address bar using **http://**:
  `http://example.com`
- The proxy fetches the page over HTTPS automatically.
- For sites that require HTTPS, still type `http://` — the proxy upgrades the connection.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `LISTEN_HOST` | `0.0.0.0` | Interface to bind to |
| `LISTEN_PORT` | `8080` | Port to listen on |

Edit these constants at the top of `app.py`.

## Security Considerations

This proxy is intended for demonstration and retro-computing use (e.g.,
virtual machines). **Do not run it on a public server.** It performs no
authentication and proxies any request it receives.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

[GPL v3](LICENSE)
