#!/usr/bin/env python3
"""Read-only smoke tests of the actual public RoleHint deployment.

No fake Telegram identities, no user writes and no secrets.
Exit nonzero if the deployed service is not healthy or private-beta
access protections are missing.
"""
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://rolehint-api-worker-production.up.railway.app"
SITE = "https://dokarpov.github.io/rolehint/site/"

def fetch(url, method="GET"):
    try:
        with urlopen(Request(url, method=method, headers={"User-Agent": "RoleHint-Release-Smoke/1.0"}), timeout=15) as r:
            return r.status, r.geturl(), r.read(400000).decode("utf-8", errors="replace")
    except HTTPError as ex:
        return ex.code, ex.geturl(), ex.read(10000).decode("utf-8", errors="replace")

def assert_http(name, url, expected, contains=None):
    code, final_url, body = fetch(url)
    ok = code == expected and (contains is None or contains in body)
    print(("PASS" if ok else "FAIL") + f" {name}: HTTP {code} {final_url}")
    if not ok:
        raise AssertionError(f"{name}: expected HTTP {expected}, marker {contains!r}; got {code}")
    return body

def main():
    health = json.loads(assert_http("backend health", API + "/health", 200, '"ok":true'))
    assert health["ok"] is True
    assert_http("Mini App loads", API + "/miniapp/", 200, "X-Telegram-Init-Data")
    assert_http("Mini App slashless URL", API + "/miniapp", 200, "X-Telegram-Init-Data")
    assert_http("Mini App config", API + "/miniapp/config.js", 200)
    assert_http("Mini App enhancement JS", API + "/miniapp/ux-v2.js", 200)
    assert_http("Mini App styling", API + "/miniapp/ux-v2.css", 200)
    assert_http("web application", API + "/webapp/", 200, "Find work worth")
    assert_http("Telegram web-login POST route exists", API + "/web-api/telegram/begin", 405)
    assert_http("Telegram code verification POST route exists", API + "/web-api/telegram/complete", 405)
    assert_http("anonymous job review denied", API + "/web-api/jobs/missing/review", 401)
    assert_http("anonymous application export denied", API + "/web-api/jobs/missing/export", 401)
    assert_http("web authentication availability", API + "/web-api/auth-status", 200, "email_login_available")
    assert_http("anonymous web profile denied", API + "/web-api/me", 401)
    assert_http("anonymous CV denied", API + "/web-api/cv", 401)
    assert_http("anonymous application history denied", API + "/web-api/release-state", 401)
    assert_http("anonymous bootstrap blocked", API + "/me/bootstrap", 401)
    assert_http("legacy evidence blocked", API + "/evidence", 503)
    assert_http("marketing website links to real web app", SITE, 200, API + "/webapp/")
    print("Live read-only checks passed; this does not certify authenticated E2E.")

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, URLError) as exc:
        print("FAIL", repr(exc), file=sys.stderr)
        sys.exit(1)
