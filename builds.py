"""Item suggestions for the "while you're dead / paused" tips card.

Data: OpenDota's per-hero item popularity (what players buy most at the
start / early / mid / late stage of a game). It comes from regular
matches, not Turbo, so the stage boundaries below are squeezed to fit
Turbo's faster clock. It's popularity, not win rate.

Verified 2026-09-25:
- /api/heroes/{hero_id}/itemPopularity -> {"start_game_items": {"16": 107,
  ...}, "early_game_items": ..., "mid_game_items": ..., "late_game_items":}
  keyed by item id.
- /api/constants/items -> {"blink": {"id": 1, "dname": "Blink Dagger",
  "qual": "component", "cost": 2250, "img": "/apps/.../blink.png?t=..."}}
"""

import json
import time

import opendota

# (key, label, starts at Turbo clock second). Regular Dota's "early" is
# roughly the first 10 minutes and "mid" runs to ~25; Turbo gets there in
# about half the time.
STAGES = [("start", "Starting items", -9999), ("early", "Early game", 0),
          ("mid", "Mid game", 300), ("late", "Late game", 720)]
POP_KEYS = {"start": "start_game_items", "early": "early_game_items",
            "mid": "mid_game_items", "late": "late_game_items"}

ITEMS_MAX_AGE = 7 * 86400
POP_MAX_AGE = 86400


def stage_for(clock):
    """Index into STAGES for an in-game clock (seconds)."""
    idx = 0
    for i, (_, _, start) in enumerate(STAGES):
        if clock >= start:
            idx = i
    return idx


def _fresh(path, max_age):
    try:
        return time.time() - path.stat().st_mtime < max_age
    except OSError:
        return False


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def load_items(path, allow_fetch=True):
    """{item id (str): {"key", "name", "cost", "qual", "img"}}, cached for a
    week. Returns the stale cache (or None) if the network is down."""
    if _fresh(path, ITEMS_MAX_AGE) or not allow_fetch:
        cached = _read(path)
        if cached and all("created" in v for v in cached.values()):
            return cached
    try:
        raw = opendota._get("/constants/items")
    except Exception:
        return _read(path)
    items = {}
    for key, v in raw.items():
        if isinstance(v, dict) and isinstance(v.get("id"), int):
            img = (v.get("img") or "").split("?")[0]
            items[str(v["id"])] = {
                "key": key, "name": v.get("dname") or key,
                "cost": v.get("cost") or 0, "qual": v.get("qual"),
                "img": opendota.CDN + img if img else "",
                "components": [c for c in (v.get("components") or [])
                               if isinstance(c, str)],
                "created": bool(v.get("created"))}
    _write(path, items)
    return items


def load_popularity(hero_id, folder, allow_fetch=True):
    """Item popularity for one hero, cached for a day."""
    path = folder / f"{int(hero_id)}.json"
    if _fresh(path, POP_MAX_AGE) or not allow_fetch:
        cached = _read(path)
        if cached:
            return cached
    try:
        data = opendota._get(f"/heroes/{int(hero_id)}/itemPopularity")
    except Exception:
        return _read(path)
    if isinstance(data, dict) and "mid_game_items" in data:
        _write(path, data)
        return data
    return _read(path)


def _useful(item, stage):
    """Leave out things nobody needs a reminder for."""
    if not item or item["key"].startswith(("recipe_", "ward_")):
        return False
    if item["qual"] == "consumable" or not item["cost"]:
        return False
    if stage in ("mid", "late") and item["cost"] < 900:
        return False            # no Magic Sticks in the late-game list
    return True


def _ranked(pop, items, stage):
    counts = (pop or {}).get(POP_KEYS[stage]) or {}
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    return [items[str(i)] for i, _ in ranked if str(i) in items]


def top_items(pop, items, stage, n, skip=()):
    """The n most-bought useful items for a stage.

    OpenDota counts every purchase, parts included, so Ogre Axe and Point
    Booster show up next to the Aghanim's Scepter they become. Drop a part
    when something it builds into is also popular now or in the next stage.
    """
    stage_keys = [k for k, _, _ in STAGES]
    later = stage_keys[stage_keys.index(stage):stage_keys.index(stage) + 2]
    popular = {it["key"] for st in later for it in _ranked(pop, items, st)[:20]}
    parents = {}
    for it in items.values():
        for comp in it.get("components") or []:
            parents.setdefault(comp, set()).add(it["key"])
    out = []
    for item in _ranked(pop, items, stage):
        if not _useful(item, stage) or item["key"] in skip:
            continue
        if stage != "start" and parents.get(item["key"], set()) & popular:
            continue
        out.append(item)
        if len(out) == n:
            break
    return out


def recommend(pop, items, clock, owned):
    """What to show on the tips card.

    owned: set of item keys the player has (inventory, backpack, stash).
    Returns {"stage": label, "now": [...], "next_stage": label or None,
    "next": [...]}, each item a dict with "key", "name", "img", "owned".
    """
    if not pop or not items:
        return None
    i = stage_for(clock)
    stage, label, _ = STAGES[i]
    now = top_items(pop, items, stage, 5)
    result = {"stage": label, "now": [dict(it, owned=it["key"] in owned)
                                      for it in now],
              "next_stage": None, "next": []}
    if i + 1 < len(STAGES):
        nstage, nlabel, _ = STAGES[i + 1]
        skip = {it["key"] for it in now} | set(owned)
        result["next_stage"] = nlabel
        result["next"] = [dict(it, owned=False)
                          for it in top_items(pop, items, nstage, 4, skip)]
    return result


def is_finished(key, items):
    """True for an item worth announcing when bought: something built from
    parts (Phase Boots, Aghanim's, Sange) or a big single item (Blink
    Dagger, Ultimate Orb). Not parts like Ogre Axe, consumables, recipes
    or neutral items."""
    item = next((it for it in (items or {}).values() if it["key"] == key),
                None)
    if key == "aghanims_shard":
        return True
    if not _useful(item, "mid"):
        return False
    return bool(item.get("created")) or item["cost"] >= 2000


def next_buys(rec, n=3):
    """Up to n popular items not owned yet: this stage first, then next."""
    if not rec:
        return []
    out = [it for it in rec["now"] if not it["owned"]]
    out += [it for it in rec["next"] if it not in out]
    return out[:n]
