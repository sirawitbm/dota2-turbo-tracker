"""Check GitHub for a newer release. Only reads; never downloads or runs
anything - the app just offers a link to the release page.

GitHub allows 60 unauthenticated API calls an hour per IP; we make one at
start and one every few hours.
"""

import json
import re
import urllib.error
import urllib.request

REPO = "sirawitbm/dota2-turbo-tracker"
LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"


def parse_version(text):
    """'v0.1.2' / '0.1.2' -> (0, 1, 2), or None if it isn't X.Y.Z."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def latest_release(timeout=10):
    """(version like '0.1.2', page url) of the newest published release, or
    None on any network/API trouble - an update check must never get in the
    way of the app."""
    req = urllib.request.Request(LATEST, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "turbo-tracker-update-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if data.get("draft") or data.get("prerelease"):
        return None
    version = parse_version(data.get("tag_name"))
    if not version:
        return None
    url = data.get("html_url") or RELEASES_PAGE
    if not url.startswith(f"https://github.com/{REPO}/"):
        url = RELEASES_PAGE        # only ever open our own releases page
    return ".".join(map(str, version)), url
