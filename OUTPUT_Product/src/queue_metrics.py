"""
UiPath Queue Metrics Service - KEDA External Scaler

Exposes UiPath Orchestrator queue depth as KEDA external scaler metrics.
KEDA polls GET /scale to decide how many Jobs to create.

Endpoints:
  GET /scale  - Returns queue depth metric for KEDA
  GET /health - Health check

Required env vars:
  UIPATH_ORCHESTRATOR_URL - Orchestrator base URL
  UIPATH_TENANT           - Tenant name
  UIPATH_CLIENT_ID        - OAuth client ID
  UIPATH_CLIENT_SECRET    - OAuth client secret

Optional env vars:
  PORT                    - HTTP port (default 8080)
  POLL_INTERVAL           - Cache TTL in seconds (default 5)
"""

import os
import time
import json
import logging
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("uipath-queue-metrics")

ORCHESTRATOR_URL = os.environ["UIPATH_ORCHESTRATOR_URL"]
TENANT = os.environ["UIPATH_TENANT"]
CLIENT_ID = os.environ["UIPATH_CLIENT_ID"]
CLIENT_SECRET = os.environ["UIPATH_CLIENT_SECRET"]
PORT = int(os.environ.get("PORT", "8080"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))

# Cache
_cache = {"depth": 0, "fetched_at": 0}
_token_cache = {"token": None, "expires_at": 0}


def get_access_token():
    """Get OAuth token from UiPath Orchestrator."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    token_url = f"{ORCHESTRATOR_URL}/identity/connect/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(token_url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            _token_cache["token"] = body["access_token"]
            _token_cache["expires_at"] = time.time() + body.get("expires_in", 3600)
            return _token_cache["token"]
    except Exception as e:
        log.error("Failed to get token: %s", e)
        raise


def get_queue_depth(queue_name: str) -> int:
    """Query Orchestrator for queue item count (New state)."""
    token = get_access_token()

    # OData query for queue items in New state
    url = (
        f"{ORCHESTRATOR_URL}/{TENANT}/odata/QueueItems"
        f"?$filter=QueueDefinition/Name eq '{queue_name}' and Status eq 'New'"
        f"&$count=true&$top=0"
    )

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("@odata.count", 0)
    except Exception as e:
        log.error("Failed to query queue '%s': %s", queue_name, e)
        return 0


class ScalerHandler(BaseHTTPRequestHandler):
    """KEDA external scaler HTTP handler."""

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "healthy"})
        elif self.path.startswith("/scale"):
            # Parse queue name from query string
            queue_name = self._get_param("queueName", "default")
            now = time.time()

            # Use cached value if fresh
            if now - _cache["fetched_at"] < POLL_INTERVAL:
                depth = _cache["depth"]
            else:
                depth = get_queue_depth(queue_name)
                _cache["depth"] = depth
                _cache["fetched_at"] = now

            self._respond(200, {
                "metricValues": [{"metricName": "queueDepth", "metricValue": depth}],
                "queueDepth": depth,
            })
        else:
            self._respond(404, {"error": "not found"})

    def _get_param(self, name: str, default: str = "") -> str:
        from urllib.parse import urlparse, parse_qs
        params = parse_qs(urlparse(self.path).query)
        return params.get(name, [default])[0]

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), ScalerHandler)
    log.info("Queue metrics service listening on :%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.server_close()
