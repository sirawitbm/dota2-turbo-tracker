"""Turn the stream of Dota GSI messages into finished matches.

Pure logic, no network or windows, so it can be tested by replaying a
recorded capture.

What the real data looks like (see PLAN.md):
- map.game_state walks through HERO_SELECTION ... GAME_IN_PROGRESS ->
  POST_GAME.
- map.win_team flips from "none" to "radiant"/"dire" when the Ancient dies.
- There is no game mode in GSI; that comes from OpenDota later.
"""

import json
import time

IN_GAME = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
PRE_GAME = "DOTA_GAMERULES_STATE_PRE_GAME"
POST_GAME = "DOTA_GAMERULES_STATE_POST_GAME"


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def owned_items(items):
    """Keys (no "item_" prefix) of everything the player has: inventory,
    backpack, stash, neutral slot."""
    owned = set()
    for slot, info in items.items():
        name = (info or {}).get("name", "empty") if isinstance(info, dict) else "empty"
        if name != "empty" and slot.startswith(("slot", "stash", "neutral")):
            owned.add(name[5:] if name.startswith("item_") else name)
    return owned


def item_names(items):
    """Names of the six main inventory slots plus the neutral item."""
    names = []
    for slot in ["slot0", "slot1", "slot2", "slot3", "slot4", "slot5",
                 "neutral0"]:
        name = (items.get(slot) or {}).get("name", "empty")
        if name != "empty":
            names.append(name)
    return names


class MatchWatcher:
    """Feed it every GSI message; it hands back a match when one ends."""

    def __init__(self):
        self.live = None          # dict describing the game in progress
        self.finished_ids = set() # never report the same match twice

    def feed(self, data, now=None):
        """Process one message. Returns a finished match dict or None."""
        now = time.time() if now is None else now
        game_map = data.get("map") or {}
        player = data.get("player") or {}
        hero = data.get("hero") or {}

        # Spectating or the main menu: player has no personal stats.
        if not game_map or "kills" not in player or not hero.get("name"):
            if not game_map:
                self.live = None  # left the game / back in the menu
            return None

        match_id = str(game_map.get("matchid") or "")
        if not match_id or match_id == "0":
            return None
        state = game_map.get("game_state", "")

        self.live = {
            "match_id": match_id,
            "state": state,
            "clock": _int(game_map.get("clock_time")) or 0,
            "hero_id": _int(hero.get("id")),
            "hero_internal": hero.get("name"),
            "level": _int(hero.get("level")),
            "alive": bool(hero.get("alive", True)),
            "respawn": _int(hero.get("respawn_seconds")) or 0,
            "team": player.get("team_name"),
            "kills": _int(player.get("kills")) or 0,
            "deaths": _int(player.get("deaths")) or 0,
            "assists": _int(player.get("assists")) or 0,
            "last_hits": _int(player.get("last_hits")) or 0,
            "denies": _int(player.get("denies")) or 0,
            "gpm": _int(player.get("gpm")) or 0,
            "xpm": _int(player.get("xpm")) or 0,
            "radiant_score": _int(game_map.get("radiant_score")),
            "dire_score": _int(game_map.get("dire_score")),
            "items": item_names(data.get("items") or {}),
            "owned": owned_items(data.get("items") or {}),
            "paused": bool(game_map.get("paused")),
        }

        win_team = game_map.get("win_team") or "none"
        if win_team == "none" or match_id in self.finished_ids:
            return None

        self.finished_ids.add(match_id)
        live = self.live
        won = None
        if live["team"] in ("radiant", "dire"):
            won = 1 if live["team"] == win_team else 0
        return {
            "match_id": match_id,
            "ended_at": int(now),
            "hero_id": live["hero_id"],
            "hero_internal": live["hero_internal"],
            "won": won,
            "team": live["team"],
            "duration": live["clock"],
            "level": live["level"],
            "kills": live["kills"],
            "deaths": live["deaths"],
            "assists": live["assists"],
            "last_hits": live["last_hits"],
            "denies": live["denies"],
            "gpm": live["gpm"],
            "xpm": live["xpm"],
            "radiant_score": live["radiant_score"],
            "dire_score": live["dire_score"],
            "items": json.dumps(live["items"]),
        }

    def status(self):
        """Short description of what is happening right now, or None."""
        return dict(self.live) if self.live else None
