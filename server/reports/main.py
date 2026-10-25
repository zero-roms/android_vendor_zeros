#!/usr/bin/env python3
#
# SPDX-License-Identifier: Apache-2.0
#
"""ZeroS reports server.

Receives two things from ZeroS phones and stores them in a private Cloud
Storage bucket (LEGAL.md, Privacy, describes both to users):

  POST /v1/stats        ZeroS statistics: the JSON that LineageParts sends once
                        a day when Settings > Privacy > Trust > ZeroS statistics
                        is switched on (off by default).
  POST /v1/bugreports   A bug report zip that the user chose to send from
                        ZeroS tools, with an optional description.
  GET  /healthz         Liveness check.

Standard library only. On Cloud Run it writes to the bucket named in
ZEROS_REPORTS_BUCKET with the service's own identity, which may create objects
but not read, list or delete them. With ZEROS_REPORTS_DIR set it writes to a
local folder instead (tests and local runs).

Nothing here logs request bodies or client addresses. Cloud Run's own request
log keeps the address of each request for 30 days.
"""

import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MIB = 1024 * 1024


class Limits:
    """Request limits. The daily caps bound storage and cost if the public
    endpoint is abused: at most 20 bug reports a day of at most 30 MiB each,
    kept 30 days, is under 20 GB in the worst case."""

    bugreport_max_bytes = 30 * MIB  # Cloud Run's HTTP/1 request limit is 32 MiB
    bugreport_per_address_per_hour = 3
    bugreports_per_day = 20
    description_max_chars = 2000
    stats_max_bytes = 4096
    stats_per_address_per_hour = 30
    stats_per_day = 5000


# Crockford base32 without I, L, O and U, so report IDs read back unambiguously
ID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

DEVICE_HASH = re.compile(r"^[0-9A-F]{1,64}$")
DEVICE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
ZIP_MAGIC = b"PK\x03\x04"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def clean_text(value, max_chars, allow_newlines=False):
    """Returns value as a string without control characters, or None if it is
    not a string or longer than max_chars."""
    if not isinstance(value, str) or len(value) > max_chars:
        return None
    allowed = "\n" if allow_newlines else ""
    return "".join(c for c in value if c.isprintable() or c in allowed)


def new_report_id():
    raw = "".join(secrets.choice(ID_ALPHABET) for _ in range(8))
    return raw[:4] + "-" + raw[4:]


class RateLimiter:
    """Per-address hourly limits and a global daily cap, kept in memory. The
    service runs on at most one instance (max-instances 1), so this memory is
    the whole service's view."""

    def __init__(self, per_address_per_hour, per_day):
        self.per_address_per_hour = per_address_per_hour
        self.per_day = per_day
        self.lock = threading.Lock()
        self.by_address = {}
        self.day = None
        self.day_count = 0

    def allow(self, address, now=None):
        now = time.time() if now is None else now
        today = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).date()
        with self.lock:
            if today != self.day:
                self.day = today
                self.day_count = 0
            if self.day_count >= self.per_day:
                return False
            recent = [t for t in self.by_address.get(address, []) if now - t < 3600]
            if len(recent) >= self.per_address_per_hour:
                self.by_address[address] = recent
                return False
            recent.append(now)
            self.by_address[address] = recent
            self.day_count += 1
            # Forget addresses that have been quiet for an hour
            if len(self.by_address) > 10000:
                self.by_address = {
                    a: ts for a, ts in self.by_address.items() if now - ts[-1] < 3600
                }
            return True


class DirStorage:
    """Writes objects as files under a folder (tests and local runs)."""

    def __init__(self, root):
        self.root = root

    def put(self, name, data, content_type):
        path = os.path.join(self.root, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "xb") as f:
                f.write(data)
        except FileExistsError:
            return False
        return True


class GcsStorage:
    """Writes objects to Cloud Storage through its JSON API, using the access
    token of the service's own identity from the metadata server."""

    METADATA_TOKEN_URL = (
        "http://metadata.google.internal/computeMetadata/v1/"
        "instance/service-accounts/default/token"
    )

    def __init__(self, bucket):
        self.bucket = bucket
        self.lock = threading.Lock()
        self.token = None
        self.token_expiry = 0

    def _access_token(self):
        with self.lock:
            if self.token is None or time.time() > self.token_expiry - 60:
                request = urllib.request.Request(
                    self.METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"}
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    body = json.load(response)
                self.token = body["access_token"]
                self.token_expiry = time.time() + int(body.get("expires_in", 300))
            return self.token

    def put(self, name, data, content_type):
        # ifGenerationMatch=0: create only, never overwrite. The service's
        # identity may only create objects, so an existing name fails with 412.
        url = (
            "https://storage.googleapis.com/upload/storage/v1/b/%s/o"
            "?uploadType=media&ifGenerationMatch=0&name=%s"
            % (
                urllib.parse.quote(self.bucket, safe=""),
                urllib.parse.quote(name, safe=""),
            )
        )
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": "Bearer " + self._access_token(),
                "Content-Type": content_type,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                response.read()
        except urllib.error.HTTPError as e:
            if e.code == 412:
                return False
            raise
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "zeros-reports"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 120  # seconds of socket inactivity before a slow upload is dropped

    # Set on the class by make_server()
    storage = None
    limits = Limits
    stats_limiter = None
    bugreport_limiter = None

    def log_message(self, format, *args):
        # Method, path and status only: no addresses, no bodies
        pass

    def log_request(self, code="-", size="-"):
        sys.stderr.write("%s %s %s\n" % (self.command, self.path, code))

    # Responses

    def send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, message):
        # The body was not read, so the connection cannot be reused
        self.close_connection = True
        self.send_json(code, {"error": message})

    # Request helpers

    def client_address_for_limits(self):
        # Cloud Run appends the address it saw to X-Forwarded-For, so the last
        # entry is the one a client cannot forge
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
        return self.client_address[0]

    def content_length(self):
        value = self.headers.get("Content-Length")
        if value is None or not value.isdigit():
            return None
        return int(value)

    def read_body(self, length):
        chunks = []
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, MIB))
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def media_type(self):
        return self.headers.get("Content-Type", "").split(";")[0].strip().lower()

    # Routes

    def do_GET(self):
        if self.path == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/v1/stats", "/v1/bugreports"):
            self.send_error_json(405, "use POST")
        else:
            self.send_error_json(404, "not found")

    def do_POST(self):
        if self.path == "/v1/stats":
            self.post_stats()
        elif self.path == "/v1/bugreports":
            self.post_bugreport()
        else:
            self.send_error_json(404, "not found")

    def post_stats(self):
        length = self.content_length()
        if length is None:
            return self.send_error_json(411, "Content-Length required")
        if length > self.limits.stats_max_bytes:
            return self.send_error_json(413, "too large")
        if self.media_type() != "application/json":
            return self.send_error_json(415, "expected application/json")
        if not self.stats_limiter.allow(self.client_address_for_limits()):
            return self.send_error_json(429, "too many requests")
        body = self.read_body(length)
        if body is None:
            return self.send_error_json(400, "incomplete body")
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return self.send_error_json(400, "invalid JSON")
        if not isinstance(data, dict):
            return self.send_error_json(400, "invalid JSON")

        device_hash = data.get("device_hash")
        device_name = data.get("device_name")
        if not isinstance(device_hash, str) or not DEVICE_HASH.match(device_hash.upper()):
            return self.send_error_json(400, "invalid device_hash")
        if not isinstance(device_name, str) or not DEVICE_NAME.match(device_name):
            return self.send_error_json(400, "invalid device_name")
        record = {"device_hash": device_hash.upper(), "device_name": device_name}
        for field, max_chars in (
            ("device_version", 96),
            ("device_country", 16),
            ("device_carrier", 64),
            ("device_carrier_id", 16),
        ):
            value = clean_text(data.get(field, ""), max_chars)
            if value is None:
                return self.send_error_json(400, "invalid " + field)
            record[field] = value

        now = utc_now()
        record["received"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        # One object per phone per day; a second report on the same day
        # (every boot sends one) is accepted and dropped
        name = "stats/%s/%s.json" % (now.strftime("%Y-%m-%d"), record["device_hash"])
        try:
            self.storage.put(name, json.dumps(record).encode(), "application/json")
        except Exception as e:  # storage unavailable: let the phone retry later
            sys.stderr.write("stats storage error: %s\n" % type(e).__name__)
            return self.send_error_json(503, "try again later")
        self.send_json(200, {})

    def post_bugreport(self):
        length = self.content_length()
        if length is None:
            return self.send_error_json(411, "Content-Length required")
        if length > self.limits.bugreport_max_bytes:
            return self.send_error_json(413, "too large")
        if length < len(ZIP_MAGIC):
            return self.send_error_json(400, "not a zip file")
        if self.media_type() != "application/zip":
            return self.send_error_json(415, "expected application/zip")

        version = clean_text(self.headers.get("X-ZeroS-Version", ""), 64)
        device = self.headers.get("X-ZeroS-Device", "")
        if version is None or not DEVICE_NAME.match(device):
            return self.send_error_json(400, "invalid version or device")
        try:
            description = base64.b64decode(
                self.headers.get("X-ZeroS-Description", ""), validate=True
            ).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return self.send_error_json(400, "invalid description")
        description = clean_text(
            description, self.limits.description_max_chars, allow_newlines=True
        )
        if description is None:
            return self.send_error_json(400, "description too long")

        if not self.bugreport_limiter.allow(self.client_address_for_limits()):
            return self.send_error_json(429, "too many requests")
        body = self.read_body(length)
        if body is None:
            return self.send_error_json(400, "incomplete body")
        if not body.startswith(ZIP_MAGIC):
            return self.send_error_json(400, "not a zip file")

        now = utc_now()
        report_id = new_report_id()
        prefix = "bugreports/%s/%s" % (now.strftime("%Y-%m-%d"), report_id)
        metadata = {
            "id": report_id,
            "received": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": version,
            "device": device,
            "description": description,
            "size": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        try:
            if not self.storage.put(prefix + ".zip", body, "application/zip"):
                return self.send_error_json(503, "try again")
            self.storage.put(prefix + ".json", json.dumps(metadata).encode(), "application/json")
        except Exception as e:
            sys.stderr.write("bugreport storage error: %s\n" % type(e).__name__)
            return self.send_error_json(503, "try again later")
        sys.stderr.write("bug report %s stored (%d bytes)\n" % (report_id, len(body)))
        self.send_json(201, {"id": report_id})


def make_server(address, storage, limits=Limits):
    handler = type(
        "ConfiguredHandler",
        (Handler,),
        {
            "storage": storage,
            "limits": limits,
            "stats_limiter": RateLimiter(
                limits.stats_per_address_per_hour, limits.stats_per_day
            ),
            "bugreport_limiter": RateLimiter(
                limits.bugreport_per_address_per_hour, limits.bugreports_per_day
            ),
        },
    )
    server = ThreadingHTTPServer(address, handler)
    server.daemon_threads = True
    return server


def main():
    bucket = os.environ.get("ZEROS_REPORTS_BUCKET")
    folder = os.environ.get("ZEROS_REPORTS_DIR")
    if bucket:
        storage = GcsStorage(bucket)
    elif folder:
        storage = DirStorage(folder)
    else:
        sys.exit("Set ZEROS_REPORTS_BUCKET (Cloud Run) or ZEROS_REPORTS_DIR (local)")
    port = int(os.environ.get("PORT", "8080"))
    server = make_server(("", port), storage)
    sys.stderr.write("zeros-reports listening on port %d\n" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()
