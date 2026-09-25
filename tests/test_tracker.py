"""Logic tests. Run:  python -m unittest discover tests

Payloads here are hand-made in the shape of real GSI data (see PLAN.md),
with no Steam ids.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gsi import MatchWatcher  # noqa: E402
from store import Store  # noqa: E402


def payload(state, win_team="none", match_id="123", kills=5, team="radiant",
            hero="npc_dota_hero_pudge"):
    return {
        "provider": {"appid": 570},
        "map": {"matchid": match_id, "game_state": state, "win_team": win_team,
                "clock_time": 900, "radiant_score": 20, "dire_score": 10},
        "player": {"kills": kills, "deaths": 2, "assists": 7, "last_hits": 90,
                   "denies": 4, "gpm": 800, "xpm": 900, "team_name": team},
        "hero": {"id": 14, "name": hero, "level": 22, "alive": True},
        "items": {"slot0": {"name": "item_blink"},
                  "slot1": {"name": "empty"}},
    }


class WatcherTests(unittest.TestCase):
    def test_reports_win_once(self):
        w = MatchWatcher()
        self.assertIsNone(w.feed(payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS")))
        m = w.feed(payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", "radiant"))
        self.assertEqual(m["won"], 1)
        self.assertEqual(m["kills"], 5)
        self.assertEqual(m["items"], '["item_blink"]')
        # POST_GAME messages keep coming: must not report it again
        self.assertIsNone(w.feed(payload("DOTA_GAMERULES_STATE_POST_GAME",
                                         "radiant")))

    def test_loss(self):
        w = MatchWatcher()
        m = w.feed(payload("DOTA_GAMERULES_STATE_POST_GAME", "radiant",
                           team="dire"))
        self.assertEqual(m["won"], 0)

    def test_ignores_menu_and_spectating(self):
        w = MatchWatcher()
        self.assertIsNone(w.feed({"provider": {"appid": 570}}))
        spectate = payload("DOTA_GAMERULES_STATE_POST_GAME", "radiant")
        spectate["player"] = {"team2": {}, "team3": {}}   # spectator shape
        self.assertIsNone(w.feed(spectate))

    def test_leaving_clears_live_status(self):
        w = MatchWatcher()
        w.feed(payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"))
        self.assertIsNotNone(w.status())
        w.feed({"provider": {}, "player": {}})
        self.assertIsNone(w.status())


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "t.db")

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def add(self, match_id, won, hero="npc_dota_hero_pudge"):
        w = MatchWatcher()
        m = w.feed(payload("DOTA_GAMERULES_STATE_POST_GAME", "radiant",
                           match_id=match_id, hero=hero,
                           team="radiant" if won else "dire"))
        return self.store.add_match(m)

    def test_duplicates_ignored(self):
        self.assertTrue(self.add("1", True))
        self.assertFalse(self.add("1", True))
        self.assertEqual(self.store.summary()["games"], 1)

    def test_hero_facts_and_turbo_filter(self):
        self.add("1", True)
        self.add("2", False)
        self.add("3", True, hero="npc_dota_hero_axe")
        facts = self.store.hero_facts("npc_dota_hero_pudge")
        self.assertEqual((facts["today"], facts["wins"], facts["losses"]),
                         (2, 1, 1))
        self.assertEqual(self.store.summary(turbo_only=True)["games"], 0)
        self.store.set_mode("1", 23, "found")
        self.assertEqual(self.store.summary(turbo_only=True)["games"], 1)
        self.assertEqual(len(self.store.pending_modes()), 2)


class VersionTests(unittest.TestCase):
    def test_version_line_matches_build_regex(self):
        # tools/project.ps1 reads the version with this same pattern
        import re
        src = (Path(__file__).resolve().parent.parent
               / "turbo_tracker.py").read_text(encoding="utf-8")
        self.assertRegex(src, re.compile(
            r'^__version__\s*=\s*"\d+\.\d+\.\d+"', re.M))


if __name__ == "__main__":
    unittest.main()
