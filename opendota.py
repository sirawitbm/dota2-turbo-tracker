"""Small OpenDota helpers (free API, no key needed).

Verified 2026-09-25:
- /api/constants/game_mode: 23 = game_mode_turbo
- /api/matches/{id}: 404 {"error":"Not Found"} for bot/lobby games
- /api/constants/heroes: {"53": {"localized_name": "Nature's Prophet",
  "name": "npc_dota_hero_furion", ...}}
"""

import json
import urllib.error
import urllib.request

API = "https://api.opendota.com/api"
HEADERS = {"User-Agent": "turbo-tracker (github.com/sirawitbm)"}

MODE_NAMES = {
    1: "All Pick", 2: "Captains Mode", 3: "Random Draft", 4: "Single Draft",
    5: "All Random", 12: "Least Played", 16: "Captains Draft",
    18: "Ability Draft", 19: "Event", 20: "All Random Deathmatch",
    21: "1v1 Mid", 22: "Ranked All Pick", 23: "Turbo",
}


def _get(path, timeout=15):
    req = urllib.request.Request(API + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def match_mode(match_id):
    """Look up a match's game mode.

    Returns ("found", mode); ("not_found_yet", None) when OpenDota has no
    such match - either Valve hasn't published it yet (it takes a few
    minutes) or it never will (bot and lobby games); or ("retry", None) for
    network trouble. The caller decides when to give up.
    """
    try:
        data = _get(f"/matches/{match_id}")
    except urllib.error.HTTPError as err:
        return ("not_found_yet", None) if err.code == 404 else ("retry", None)
    except (urllib.error.URLError, OSError, ValueError):
        return ("retry", None)
    mode = data.get("game_mode")
    return ("found", mode) if isinstance(mode, int) else ("retry", None)


CDN = "https://cdn.cloudflare.steamstatic.com"


def hero_names():
    """{internal name: {"name": display name, "img": portrait url}}, e.g.
    npc_dota_hero_furion -> Nature's Prophet. Raises on network trouble;
    callers cache the result."""
    data = _get("/constants/heroes")
    out = {}
    for h in data.values():
        if isinstance(h, dict) and "name" in h:
            img = (h.get("img") or "").split("?")[0]
            out[h["name"]] = {"name": h.get("localized_name", h["name"]),
                              "img": CDN + img if img else ""}
    return out


def download(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
