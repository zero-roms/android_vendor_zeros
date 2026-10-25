#!/usr/bin/env python3
#
# SPDX-License-Identifier: Apache-2.0
#
"""Tests for the ZeroS reports server, run against a local folder:

    python3 -I test_main.py
"""

import base64
import http.client
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main  # noqa: E402


class SmallLimits(main.Limits):
    bugreport_max_bytes = 64 * 1024
    bugreport_per_address_per_hour = 3
    bugreports_per_day = 5
    stats_per_address_per_hour = 4
    stats_per_day = 100


def make_zip(size=1000):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("bugreport.txt", "x" * size)
    return buffer.getvalue()


STATS = {
    "device_hash": "4F2A9C",
    "device_name": "ginkgo",
    "device_version": "24.0-20261025-UNOFFICIAL-ginkgo",
    "device_country": "IN",
    "device_carrier": "Example Carrier",
    "device_carrier_id": "40445",
}


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.server = main.make_server(
            ("127.0.0.1", 0), main.DirStorage(self.folder), SmallLimits
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.folder)

    def request(self, method, path, body=None, headers=None, forwarded="203.0.113.7"):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        all_headers = {"X-Forwarded-For": forwarded}
        all_headers.update(headers or {})
        connection.request(method, path, body=body, headers=all_headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, data

    def post_stats(self, payload=None, **kwargs):
        body = json.dumps(STATS if payload is None else payload).encode()
        return self.request(
            "POST", "/v1/stats", body, {"Content-Type": "application/json"}, **kwargs
        )

    def post_bugreport(self, body=None, description="Settings crashed", headers=None, **kwargs):
        all_headers = {
            "Content-Type": "application/zip",
            "X-ZeroS-Version": "0.5.1-20261025-UNOFFICIAL-ginkgo",
            "X-ZeroS-Device": "ginkgo",
            "X-ZeroS-Description": base64.b64encode(description.encode()).decode(),
        }
        all_headers.update(headers or {})
        return self.request(
            "POST", "/v1/bugreports", make_zip() if body is None else body, all_headers, **kwargs
        )

    def stored(self, kind):
        found = []
        for root, _, files in os.walk(os.path.join(self.folder, kind)):
            found.extend(os.path.join(root, f) for f in files)
        return sorted(found)

    # Basics

    def test_healthz(self):
        self.assertEqual(self.request("GET", "/healthz"), (200, b"ok\n"))

    def test_unknown_path(self):
        self.assertEqual(self.request("GET", "/")[0], 404)
        self.assertEqual(self.request("POST", "/v1/other", b"{}")[0], 404)

    def test_get_on_post_route(self):
        self.assertEqual(self.request("GET", "/v1/bugreports")[0], 405)

    # Statistics

    def test_stats_stored_once_per_day(self):
        self.assertEqual(self.post_stats()[0], 200)
        self.assertEqual(self.post_stats()[0], 200)
        files = self.stored("stats")
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("/4F2A9C.json"))
        with open(files[0]) as f:
            record = json.load(f)
        self.assertEqual(record["device_name"], "ginkgo")
        self.assertEqual(record["device_country"], "IN")
        self.assertIn("received", record)

    def test_stats_lowercase_hash_is_normalised(self):
        payload = dict(STATS, device_hash="abc123")
        self.assertEqual(self.post_stats(payload)[0], 200)
        self.assertTrue(self.stored("stats")[0].endswith("/ABC123.json"))

    def test_stats_rejects_bad_hash(self):
        # Bad requests count towards the hourly limit too, so each comes from its own address
        for i, bad in enumerate(("", "../etc", "XYZ", "A" * 65, 42)):
            payload = dict(STATS, device_hash=bad)
            self.assertEqual(self.post_stats(payload, forwarded="192.0.2.%d" % i)[0], 400, bad)
        self.assertEqual(self.stored("stats"), [])

    def test_stats_rejects_bad_device_name(self):
        self.assertEqual(self.post_stats(dict(STATS, device_name="gin/kgo"))[0], 400)

    def test_stats_rejects_long_field(self):
        self.assertEqual(self.post_stats(dict(STATS, device_carrier="c" * 65))[0], 400)

    def test_stats_strips_control_characters(self):
        self.post_stats(dict(STATS, device_carrier="Bad\x00\nCarrier"))
        with open(self.stored("stats")[0]) as f:
            self.assertEqual(json.load(f)["device_carrier"], "BadCarrier")

    def test_stats_rejects_wrong_type_and_json(self):
        status, _ = self.request("POST", "/v1/stats", b"{}", {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        status, _ = self.request(
            "POST", "/v1/stats", b"not json", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)
        status, _ = self.request(
            "POST", "/v1/stats", b"[1, 2]", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)

    def test_stats_too_large(self):
        payload = dict(STATS, device_version="v" * 5000)
        self.assertEqual(self.post_stats(payload)[0], 413)

    def test_stats_rate_limited_per_address(self):
        for i in range(4):
            self.assertEqual(self.post_stats(dict(STATS, device_hash="%X" % (i + 1)))[0], 200)
        self.assertEqual(self.post_stats(dict(STATS, device_hash="FF"))[0], 429)
        # Another address is not affected
        self.assertEqual(
            self.post_stats(dict(STATS, device_hash="FE"), forwarded="198.51.100.2")[0], 200
        )

    def test_forged_forwarded_address_does_not_bypass_limit(self):
        # A client-supplied X-Forwarded-For comes first; the server uses the last entry
        for i in range(4):
            self.post_stats(
                dict(STATS, device_hash="%X" % (i + 1)), forwarded="1.1.1.%d, 203.0.113.7" % i
            )
        status, _ = self.post_stats(
            dict(STATS, device_hash="FF"), forwarded="9.9.9.9, 203.0.113.7"
        )
        self.assertEqual(status, 429)

    # Bug reports

    def test_bugreport_stored_with_metadata(self):
        status, body = self.post_bugreport(description="Wi-Fi drops\nafter sleep")
        self.assertEqual(status, 201)
        report_id = json.loads(body)["id"]
        self.assertRegex(report_id, r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
        files = self.stored("bugreports")
        self.assertEqual([os.path.basename(f) for f in files], [report_id + ".json", report_id + ".zip"])
        with open(files[0]) as f:
            metadata = json.load(f)
        self.assertEqual(metadata["description"], "Wi-Fi drops\nafter sleep")
        self.assertEqual(metadata["device"], "ginkgo")
        self.assertEqual(metadata["version"], "0.5.1-20261025-UNOFFICIAL-ginkgo")
        self.assertEqual(metadata["size"], os.path.getsize(files[1]))
        self.assertEqual(len(metadata["sha256"]), 64)

    def test_bugreport_unicode_description(self):
        status, _ = self.post_bugreport(description="कैमरा बंद हो गया")
        self.assertEqual(status, 201)
        with open(self.stored("bugreports")[0], encoding="utf-8") as f:
            self.assertEqual(json.load(f)["description"], "कैमरा बंद हो गया")

    def test_bugreport_empty_description_allowed(self):
        self.assertEqual(self.post_bugreport(description="")[0], 201)

    def test_bugreport_rejects_non_zip(self):
        self.assertEqual(self.post_bugreport(body=b"MZ" + b"\0" * 100)[0], 400)
        self.assertEqual(self.stored("bugreports"), [])

    def test_bugreport_rejects_wrong_content_type(self):
        status, _ = self.post_bugreport(headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(status, 415)

    def test_bugreport_too_large(self):
        status, _ = self.post_bugreport(body=b"PK\x03\x04" + b"\0" * (64 * 1024))
        self.assertEqual(status, 413)

    def test_bugreport_bad_description(self):
        status, _ = self.post_bugreport(headers={"X-ZeroS-Description": "!!not base64!!"})
        self.assertEqual(status, 400)
        status, _ = self.post_bugreport(description="x" * 2001)
        self.assertEqual(status, 400)

    def test_bugreport_bad_device(self):
        status, _ = self.post_bugreport(headers={"X-ZeroS-Device": "../../x"})
        self.assertEqual(status, 400)

    def test_bugreport_rate_limits(self):
        for _ in range(3):
            self.assertEqual(self.post_bugreport()[0], 201)
        self.assertEqual(self.post_bugreport()[0], 429)
        # Daily cap across addresses: 5 in total
        self.assertEqual(self.post_bugreport(forwarded="198.51.100.2")[0], 201)
        self.assertEqual(self.post_bugreport(forwarded="198.51.100.3")[0], 201)
        self.assertEqual(self.post_bugreport(forwarded="198.51.100.4")[0], 429)
        self.assertEqual(len(self.stored("bugreports")), 10)

    def test_missing_content_length(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.putrequest("POST", "/v1/bugreports")
        connection.putheader("Content-Type", "application/zip")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 411)
        connection.close()


class RateLimiterTest(unittest.TestCase):
    def test_window_slides(self):
        limiter = main.RateLimiter(per_address_per_hour=2, per_day=100)
        self.assertTrue(limiter.allow("a", now=1000))
        self.assertTrue(limiter.allow("a", now=1001))
        self.assertFalse(limiter.allow("a", now=1002))
        self.assertTrue(limiter.allow("a", now=1000 + 3601))

    def test_daily_cap_resets(self):
        limiter = main.RateLimiter(per_address_per_hour=100, per_day=1)
        day = 86400 * 20000
        self.assertTrue(limiter.allow("a", now=day + 10))
        self.assertFalse(limiter.allow("b", now=day + 20))
        self.assertTrue(limiter.allow("b", now=day + 86400 + 5))


class ReportIdTest(unittest.TestCase):
    def test_format(self):
        ids = {main.new_report_id() for _ in range(200)}
        self.assertEqual(len(ids), 200)
        for report_id in ids:
            self.assertRegex(report_id, r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")


if __name__ == "__main__":
    unittest.main(verbosity=1)
