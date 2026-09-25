"""Make the README screenshots from made-up demo games.

Uses a throwaway data folder, never touches the real database, and never
writes Dota's config file. Renders the app's own windows only (no desktop,
no title bar), so nothing personal ends up in the images.

Run:  python tools/screenshots.py      -> docs/*.png
"""

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = Path(tempfile.mkdtemp(prefix="turbo-demo-"))
os.environ["TURBO_TRACKER_DATA"] = str(DEMO)
sys.path.insert(0, str(ROOT))

# Reuse hero names/portraits already downloaded by a source run, if any.
real = ROOT / "local"
if (real / "heroes.json").exists():
    shutil.copy(real / "heroes.json", DEMO / "heroes.json")
if (real / "portraits").exists():
    shutil.copytree(real / "portraits", DEMO / "portraits")
(DEMO / "settings.json").write_text(json.dumps({
    "token": "demo", "port": 3199, "recap_mode": "popup",
    "turbo_only": True}), encoding="utf-8")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import setup_gsi  # noqa: E402

# Never touch the real Dota config from here.
setup_gsi.install = lambda: None
setup_gsi.config_matches = lambda: True
setup_gsi.launch_option_set = lambda: True

import turbo_tracker as tt  # noqa: E402
import ui  # noqa: E402

# Render everything off-screen: we only grab the widgets, and nothing should
# pop up over whatever the user is doing (a Dota game, say).
_OFF = lambda self, *a, **k: self.move(-9000, -9000)
ui.RecapCard._place = _OFF
ui.TaskbarPanel._place = _OFF
ui.TipsCard.place = _OFF
ui.ItemToast.place = _OFF

H = "npc_dota_hero_"
GAMES = [  # hero, won, k, d, a, minutes, gpm, xpm, lh, hours ago
    ("pudge", 1, 14, 5, 21, 19, 912, 1040, 118, 0.3),
    ("pudge", 1, 11, 3, 17, 17, 870, 990, 101, 1.1),
    ("zuus", 0, 9, 8, 24, 23, 780, 910, 96, 1.8),
    ("pudge", 0, 6, 9, 12, 21, 690, 820, 84, 2.6),
    ("juggernaut", 1, 17, 2, 9, 18, 1105, 1150, 262, 3.4),
    ("lina", 1, 12, 4, 15, 20, 960, 1080, 190, 24),
    ("axe", 1, 10, 6, 22, 22, 820, 950, 140, 25),
    ("axe", 0, 5, 7, 18, 25, 640, 780, 120, 26),
    ("phantom_assassin", 1, 19, 3, 8, 16, 1180, 1210, 240, 48),
    ("witch_doctor", 0, 4, 10, 20, 24, 560, 700, 45, 49),
    ("sniper", 1, 13, 5, 11, 19, 990, 1020, 230, 72),
    ("ogre_magi", 1, 7, 4, 26, 21, 700, 860, 70, 73),
]
LIVE = {"hero_internal": H + "pudge", "state": tt.LIVE_STATES[0],
        "clock": 1122, "kills": 8, "deaths": 2, "assists": 11, "gpm": 845,
        "alive": True, "respawn": 0, "match_id": "demo-live"}


def seed(store):
    now = time.time()
    for i, (hero, won, k, d, a, mins, gpm, xpm, lh, ago) in enumerate(GAMES):
        store.add_match({
            "match_id": f"demo{i}", "ended_at": int(now - ago * 3600),
            "hero_id": 0, "hero_internal": H + hero, "won": won,
            "team": "radiant", "duration": mins * 60 + 17 * i % 60,
            "level": 24, "kills": k, "deaths": d, "assists": a,
            "last_hits": lh, "denies": 6, "gpm": gpm, "xpm": xpm,
            "radiant_score": 40, "dire_score": 25, "items": "[]"})
        store.set_mode(f"demo{i}", 23, "found")


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ui.apply_theme(app)
    ctl = tt.Controller(app)
    seed(ctl.store)
    ctl.refresh()
    ctl.window.resize(1080, 720)
    ctl.window.move(-3000, 60)      # off screen: we only render it
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)

    def live_status():
        ctl.last_message = time.time()
        ctl.watcher.live = dict(LIVE)
        ctl.update_status()

    def ready():
        heroes = {H + g[0] for g in GAMES}
        return all(ctl.portrait(h) is not None for h in heroes)

    tries = {"n": 0}

    def shoot():
        tries["n"] += 1
        live_status()
        if not ready() and tries["n"] < 60:
            QTimer.singleShot(500, shoot)
            return
        ctl.window.grab().save(str(docs / "main.png"))
        ctl.window.tabs.buttons["heroes"].click()
        app.processEvents()
        ctl.window.grab().save(str(docs / "heroes.png"))
        ctl.show_recap("demo0")
        QTimer.singleShot(600, finish)

    def finish():
        ctl.card.grab().save(str(docs / "recap.png"))
        ctl.settings["recap_mode"] = "panel"
        ctl.apply_recap_mode()
        ctl.watcher.live = None
        ctl.update_panel()
        app.processEvents()
        ctl.panel.grab().save(str(docs / "panel.png"))
        print("Saved docs/main.png, heroes.png, recap.png, panel.png")
        ctl.quit()

    QTimer.singleShot(800, shoot)
    app.exec()
    ctl.store.db.close()
    shutil.rmtree(DEMO, ignore_errors=True)


if __name__ == "__main__":
    main()
