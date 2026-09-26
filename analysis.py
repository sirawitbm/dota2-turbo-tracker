"""After-game damage report from OpenDota's parsed match data.

Dota's live feed (GSI) has no damage sources or types. OpenDota does, once
it has parsed the match replay: we ask it to (POST /request/{id}) when a
game ends, then fetch the match until it comes back parsed.

Verified 2026-09-26 on a parsed match (players[i]):
- damage_inflictor_received: {"null": 16410, "dragon_knight_breathe_fire":
  5712, ...}  - damage taken per spell/item; "null" = right-click attacks
- damage_taken: {"npc_dota_hero_axe": 4897, "npc_dota_badguys_tower3_mid":
  542, ...}   - damage taken per source unit
- deaths_log: [{"time": 194, "key": "npc_dota_hero_lone_druid", ...}]
- /constants/abilities: {"pudge_meat_hook": {"dname": "Meat Hook",
  "dmg_type": "Pure"}}; /constants/hero_abilities: {"npc_dota_hero_pudge":
  {"abilities": ["pudge_meat_hook", ...]}}
Not in the data: debuffs *received* ("stuns" is stun time a player dealt).
"""

import json
import time
import urllib.error
import urllib.request

import opendota

TYPES = ("Physical", "Magical", "Pure", "Other")

# Item damage types aren't in OpenDota's constants; these are the common
# damaging ones whose type is certain. Anything else counts as "Other".
ITEM_TYPES = {
    "dagon": "Magical", "radiance": "Magical", "ethereal_blade": "Magical",
    "maelstrom": "Magical", "mjollnir": "Magical", "gleipnir": "Magical",
    "shivas_guard": "Magical", "meteor_hammer": "Magical",
    "orchid": "Magical", "bloodthorn": "Magical", "cloak_of_flames": "Magical",
    "heavens_halberd": "Physical", "abyssal_blade": "Physical",
    "skull_basher": "Physical", "monkey_king_bar": "Magical",
    "javelin": "Magical", "daedalus": "Physical", "greater_crit": "Physical",
}

CONSTANTS_MAX_AGE = 7 * 86400


def _post(path, timeout=15):
    req = urllib.request.Request(opendota.API + path, data=b"", method="POST",
                                 headers=opendota.HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def request_parse(match_id):
    """Ask OpenDota to parse a match's replay. True if it took the job."""
    try:
        return bool(_post(f"/request/{int(match_id)}"))
    except (urllib.error.URLError, OSError, ValueError):
        return False


def fetch_match(match_id):
    """The match, or "missing" if OpenDota doesn't have it, or None on
    network trouble."""
    try:
        return opendota._get(f"/matches/{int(match_id)}")
    except urllib.error.HTTPError as err:
        return "missing" if err.code == 404 else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def is_parsed(match):
    return isinstance(match, dict) and bool(match.get("version")) and any(
        p.get("damage_inflictor_received") for p in match.get("players", []))


def load_abilities(path):
    """{"abilities": {key: {"name", "type"}}, "owner": {key: hero}}, cached
    for a week."""
    try:
        if time.time() - path.stat().st_mtime < CONSTANTS_MAX_AGE:
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    try:
        raw = opendota._get("/constants/abilities")
        owners = opendota._get("/constants/hero_abilities")
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    abilities = {}
    for key, v in raw.items():
        if isinstance(v, dict):
            t = v.get("dmg_type")
            abilities[key] = {"name": v.get("dname") or "",
                              "type": t if t in TYPES[:3] else "Other"}
    owner = {}
    for hero, v in owners.items():
        for ab in (v or {}).get("abilities", []) if isinstance(v, dict) else []:
            for name in (ab if isinstance(ab, list) else [ab]):
                if isinstance(name, str):       # some heroes nest lists
                    owner[name] = hero
    data = {"abilities": abilities, "owner": owner}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
    return data


def _item_base(key):
    """item_dagon_5 -> dagon; item_radiance -> radiance."""
    base = key[5:] if key.startswith("item_") else key
    for known in ITEM_TYPES:
        if base == known or base.startswith(known + "_"):
            return known
    return base


def _pretty(key):
    return key.replace("_", " ").title()


def build_report(match, hero_id, abilities, items_db=None, hero_names=None):
    """What hit you, from a parsed OpenDota match. hero_id identifies you.

    Returns {"total", "by_type": {type: amount}, "by_hero": [{"hero",
    "total", "spells", "attacks"}], "spells": [{"key", "name", "hero",
    "type", "amount"}], "other": amount from creeps/towers/summons,
    "deaths": [{"time", "killer"}]} or None if you aren't in the match.
    """
    me = next((p for p in match.get("players", [])
               if p.get("hero_id") == hero_id), None)
    if me is None:
        return None
    abil = (abilities or {}).get("abilities", {})
    owner = (abilities or {}).get("owner", {})
    item_names = {it["key"]: it["name"] for it in (items_db or {}).values()}
    hero_names = hero_names or {}

    received = me.get("damage_inflictor_received") or {}
    by_type = {t: 0 for t in TYPES}
    spells = []
    from_hero_spells = {}
    for key, amount in received.items():
        amount = int(amount or 0)
        if amount <= 0:
            continue
        if key in ("null", "", None):
            by_type["Physical"] += amount          # right-click attacks
            continue
        plain = key[5:] if key.startswith("item_") else key
        base = _item_base(key)
        # Parsed data names item damage plainly ("mjollnir", "blade_mail").
        if key.startswith("item_") or plain in item_names or base in ITEM_TYPES:
            kind = ITEM_TYPES.get(base, "Other")
            name = item_names.get(plain) or item_names.get(base) or _pretty(base)
            hero = None
        else:
            info = abil.get(key, {})
            kind = info.get("type", "Other")
            name = info.get("name") or _pretty(key)
            hero = owner.get(key)
        by_type[kind] += amount
        spells.append({"key": key, "name": name, "hero": hero,
                       "type": kind, "amount": amount})
        if hero:
            from_hero_spells[hero] = from_hero_spells.get(hero, 0) + amount
    spells.sort(key=lambda s: -s["amount"])

    by_hero, other = [], 0
    for unit, amount in (me.get("damage_taken") or {}).items():
        amount = int(amount or 0)
        if unit.startswith("npc_dota_hero_"):
            sp = min(from_hero_spells.get(unit, 0), amount)
            by_hero.append({"hero": unit, "total": amount, "spells": sp,
                            "attacks": amount - sp})
        else:
            other += amount
    by_hero.sort(key=lambda h: -h["total"])

    deaths = [{"time": d.get("time"), "killer": d.get("key")}
              for d in (me.get("deaths_log") or []) if isinstance(d, dict)]
    return {"total": sum(by_type.values()), "by_type": by_type,
            "by_hero": by_hero, "spells": spells, "other": other,
            "deaths": deaths}
