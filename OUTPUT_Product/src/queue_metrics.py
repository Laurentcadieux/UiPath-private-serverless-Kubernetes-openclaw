"""
UiPath Queue Metrics Service - KEDA External Scaler

Uses the `uip` CLI (pre-authenticated) to query UiPath Orchestrator
queue depth. KEDA polls GET /scale to decide how many Jobs to create.

Endpoints:
  GET /scale  - Returns queue depth metric for KEDA
  GET /health - Health check

Required env vars:
  UIPATH_FOLDER_PATH       - Orchestrator folder path (e.g. "Shared/LinuxRPA")

Optional env vars:
  UIPATH_QUEUE_NAME        - Default queue name
  PORT                     - HTTP port (default 8080)
  POLL_INTERVAL            - Cache TTL in seconds (default 5)
  UIP_CLI                  - Path to uip CLI (default: "uip")
"""

import os
import time
import json
import logging
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("uipath-queue-metrics")

FOLDER_PATH = os.environ.get("UIPATH_FOLDER_PATH", "Shared")
DEFAULT_QUEUE = os.environ.get("UIPATH_QUEUE_NAME", "")
PORT = int(os.environ.get("PORT", "8080"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
UIP_CLI = os.environ.get("UIP_CLI", "uip")

# Cache: { queue_name: { "depth": int, "fetched_at": float } }
_cache = {}


def run_uip(*args) -> dict:
    """Run a uip CLI command and return parsed JSON output."""
    cmd = [UIP_CLI] + list(args) + ["--output", "json"]
    log.debug("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            log.error("uip CLI error (rc=%d): %s", result.returncode, result.stderr.strip())
            return {"Result": "Failure"}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        log.error("uip CLI timed out")
        return {"Result": "Failure"}
    except json.JSONDecodeError as e:
        log.error("Failed to parse uip output: %s", e)
        return {"Result": "Failure"}
    except Exception as e:
        log.error("uip CLI error: %s", e)
        return {"Result": "Failure"}


def get_queue_depth(queue_name: str) -> int:
    """Query queue item count in New state using uip CLI."""
    now = time.time()

    # Check cache
    cached = _cache.get(queue_name)
    if cached and now - cached["fetched_at"] < POLL_INTERVAL:
        return cached["depth"]

    # Query via uip CLI — get all items to count accurately
    resp = run_uip(
        "or", "queue-items", "list",
        "--folder-path", FOLDER_PATH,
        "--queue-name", queue_name,
        "--status", "New",
        "--limit", "100",
    )

    if resp.get("Result") != "Success":
        # Return cached value on error, or 0
        depth = cached["depth"] if cached else 0
        log.warning("Using cached depth=%d for queue '%s'", depth, queue_name)
        return depth

    # Count from pagination (TotalCount if available, else data length)
    pagination = resp.get("Pagination", {})
    total = pagination.get("TotalCount", None)
    if total is not None:
        depth = int(total)
    else:
        depth = len(resp.get("Data", []))

    # Update cache
    _cache[queue_name] = {"depth": depth, "fetched_at": now}
    return depth


def list_queues() -> list:
    """List all queues in the folder."""
    resp = run_uip("or", "queues", "list", "--folder-path", FOLDER_PATH)
    if resp.get("Result") != "Success":
        return []
    return [q.get("Name", "") for q in resp.get("Data", [])]


class ScalerHandler(BaseHTTPRequestHandler):
    """KEDA external scaler HTTP handler."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._respond(200, {"status": "healthy"})

        elif parsed.path == "/scale":
            queue_name = params.get("queueName", [DEFAULT_QUEUE])[0]
            if not queue_name:
                self._respond(400, {"error": "queueName parameter required"})
                return

            depth = get_queue_depth(queue_name)
            self._respond(200, {
                "metricValues": [{"metricName": "queueDepth", "metricValue": depth}],
                "queueDepth": depth,
            })

        elif parsed.path == "/queues":
            queues = list_queues()
            self._respond(200, {"queues": queues})

        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt, *args):
        log.debug(fmt, *args)


if __name__ == "__main__":
    # Warm up: verify uip CLI is working
    resp = run_uip("user")
    if resp.get("Result") == "Success":
        user = resp.get("Data", {})
        log.info("Authenticated as %s (%s)", user.get("Name"), user.get("IdentityType"))
    else:
        log.warning("uip CLI not authenticated — queue queries will fail")

    server = HTTPServer(("0.0.0.0", PORT), ScalerHandler)
    log.info("Queue metrics service listening on :%d (folder: %s)", PORT, FOLDER_PATH)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.server_close()
