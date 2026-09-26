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
        # not checked yet: still shown under Turbo only
        self.assertEqual(self.store.summary(turbo_only=True)["games"], 3)
        self.store.set_mode("1", 23, "found")
        self.store.set_mode("2", 1, "found")            # All Pick: drops out
        self.store.set_mode("3", None, "not_public")    # bot game: drops out
        self.assertEqual(self.store.summary(turbo_only=True)["games"], 1)
        self.assertEqual(len(self.store.matches(turbo_only=True)), 1)
        self.assertEqual(len(self.store.pending_modes()), 0)   # all resolved


class BuildTests(unittest.TestCase):
    ITEMS = {
        "1": {"key": "blink", "name": "Blink Dagger", "cost": 2250,
              "qual": "component", "img": "", "components": []},
        "44": {"key": "tango", "name": "Tango", "cost": 90,
               "qual": "consumable", "img": "", "components": []},
        "29": {"key": "boots", "name": "Boots of Speed", "cost": 500,
               "qual": "component", "img": "", "components": []},
        "2": {"key": "ogre_axe", "name": "Ogre Axe", "cost": 1000,
              "qual": "component", "img": "", "components": []},
        "108": {"key": "ultimate_scepter", "name": "Aghanim's Scepter",
                "cost": 4200, "qual": "rare", "img": "",
                "components": ["ogre_axe"]},
        "13": {"key": "recipe_x", "name": "Recipe", "cost": 500,
               "qual": None, "img": "", "components": []},
        "36": {"key": "magic_wand", "name": "Magic Wand", "cost": 460,
               "qual": "common", "img": "", "components": []},
    }
    POP = {"start_game_items": {"44": 90, "29": 10},
           "early_game_items": {"29": 50, "36": 40, "13": 30},
           "mid_game_items": {"2": 60, "1": 50, "36": 40, "108": 30},
           "late_game_items": {"108": 20, "1": 10}}

    def test_stages_squeezed_for_turbo(self):
        from builds import STAGES, stage_for
        names = [STAGES[stage_for(c)][0] for c in (-60, 0, 299, 300, 719, 720)]
        self.assertEqual(names, ["start", "early", "early", "mid", "mid", "late"])

    def test_filters_and_owned(self):
        from builds import recommend
        rec = recommend(self.POP, self.ITEMS, 400, {"blink"})
        now = [(i["key"], i["owned"]) for i in rec["now"]]
        # Ogre Axe hidden (its Scepter is popular), Magic Wand too cheap
        # for mid game, owned Blink ticked.
        self.assertEqual(now, [("blink", True), ("ultimate_scepter", False)])
        self.assertEqual(rec["next_stage"], "Late game")
        # nothing new in late that isn't already shown/owned
        self.assertEqual(rec["next"], [])
        early = recommend(self.POP, self.ITEMS, 60, set())
        self.assertEqual([i["key"] for i in early["now"]],
                         ["boots", "magic_wand"])      # recipe dropped
        start = recommend(self.POP, self.ITEMS, -30, set())
        self.assertEqual([i["key"] for i in start["now"]], ["boots"])  # no tango

    def test_finished_items(self):
        from builds import is_finished
        items = {k: dict(v, created=v["key"] == "ultimate_scepter")
                 for k, v in self.ITEMS.items()}
        self.assertTrue(is_finished("ultimate_scepter", items))   # built
        self.assertTrue(is_finished("blink", items))              # big single
        self.assertFalse(is_finished("ogre_axe", items))          # a part
        self.assertFalse(is_finished("tango", items))             # consumable
        self.assertFalse(is_finished("recipe_x", items))
        self.assertFalse(is_finished("magic_wand", items))        # cheap
        self.assertFalse(is_finished("not_an_item", items))

    def test_next_buys_skips_owned(self):
        from builds import next_buys, recommend
        rec = recommend(self.POP, self.ITEMS, 60, {"boots"})
        # this stage first (not owned), then the next stage fills it up
        self.assertEqual([i["key"] for i in next_buys(rec, 3)],
                         ["magic_wand", "blink", "ultimate_scepter"])
        self.assertEqual(next_buys(None), [])

    def test_no_data(self):
        from builds import recommend
        self.assertIsNone(recommend(None, self.ITEMS, 100, set()))

    def test_watcher_reports_owned_and_paused(self):
        w = MatchWatcher()
        p = payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS")
        p["map"]["paused"] = True
        p["items"]["stash0"] = {"name": "item_boots"}
        w.feed(p)
        self.assertTrue(w.status()["paused"])
        self.assertEqual(w.status()["owned"], {"blink", "boots"})


class LaunchOptionTests(unittest.TestCase):
    VDF = '''"UserLocalConfigStore"
{
    "Software"
    {
        "Valve"
        {
            "Steam"
            {
                "apps"
                {
                    "440"
                    {
                        "LaunchOptions"     "-gamestateintegration"
                    }
                    "570"
                    {
                        "LastPlayed"        "1790000000"
                        "LaunchOptions"     "%s"
                    }
                }
            }
        }
    }
}
'''

    def test_reads_dota_only(self):
        from setup_gsi import dota_launch_options
        self.assertEqual(dota_launch_options(self.VDF % "-novid -console"),
                         "-novid -console")
        # the flag on another game (440) must not count for Dota
        opts = dota_launch_options(self.VDF % "-novid")
        self.assertNotIn("-gamestateintegration", opts.split())

    def test_flag_found(self):
        from setup_gsi import dota_launch_options
        opts = dota_launch_options(self.VDF % "-novid -gamestateintegration")
        self.assertIn("-gamestateintegration", opts.split())

    def test_no_dota_block(self):
        from setup_gsi import dota_launch_options
        self.assertIsNone(dota_launch_options('"UserLocalConfigStore" { }'))
        self.assertIsNone(dota_launch_options("garbage {{{"))


class DeathRecapTests(unittest.TestCase):
    def test_summary(self):
        from gsi import summarize_death
        S = frozenset({"stunned"})
        samples = [(0.0, 1000, 1000, frozenset()), (1.0, 1000, 1000, frozenset()),
                   (1.5, 700, 1000, S), (2.0, 400, 1000, S),
                   (2.5, 450, 1000, frozenset()), (3.0, 0, 1000, frozenset())]
        d = summarize_death(samples, clock=600)
        self.assertEqual(d["clock"], 600)
        self.assertAlmostEqual(d["window"], 2.0)      # last full HP at t=1.0
        self.assertEqual(d["damage"], 1000 + 50)      # drops only
        self.assertEqual(d["heal"], 50)
        self.assertEqual(d["controls"], {"stunned": 1.0})
        self.assertEqual(d["from_pct"], 100)
        self.assertIsNone(summarize_death([], 0))

    def test_watcher_records_deaths(self):
        w = MatchWatcher()
        t = 0.0
        for hp in (900, 900, 500, 100):
            p = payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS")
            p["hero"].update(health=hp, max_health=900, alive=True,
                             stunned=hp == 500)
            w.feed(p, now=t)
            t += 0.5
        dead = payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS")
        dead["hero"].update(health=0, max_health=900, alive=False)
        w.feed(dead, now=t)
        w.feed(dead, now=t + 0.5)                     # still dead: no new recap
        self.assertEqual(len(w.deaths), 1)
        self.assertEqual(w.deaths[0]["controls"], {"stunned": 0.5})
        nxt = payload("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", match_id="999")
        w.feed(nxt, now=t + 1)
        self.assertEqual(w.deaths, [])                # new match: fresh list


class UpdateTests(unittest.TestCase):
    def test_version_compare(self):
        from updates import is_newer, parse_version
        self.assertEqual(parse_version("v0.1.2"), (0, 1, 2))
        self.assertIsNone(parse_version("v1.0-beta"))
        self.assertTrue(is_newer("v0.1.10", "0.1.9"))   # not string order
        self.assertTrue(is_newer("1.0.0", "0.9.9"))
        self.assertFalse(is_newer("v0.1.1", "0.1.1"))
        self.assertFalse(is_newer("v0.1.0", "0.1.1"))
        self.assertFalse(is_newer("garbage", "0.1.1"))


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
