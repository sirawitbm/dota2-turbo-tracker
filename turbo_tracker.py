"""Turbo Tracker - logs your Dota 2 games and shows a recap when one ends.

Run:  python turbo_tracker.py      (or double-click "Turbo Tracker.bat")

Reads only what Dota's official Game State Integration sends about your own
hero. It never touches the game: no input, no memory reading.
"""

import json
import os
import queue
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

import builds
import opendota
import setup_gsi
import ui
import updates
import winutil
from gsi import MatchWatcher
from paths import (DATA as LOCAL, DB_PATH, HEROES_CACHE, INSTANCE, PORTRAITS,
                   SETTINGS)
from store import Store, start_of_today

__version__ = "0.1.5"

UPDATE_EVERY_MS = 6 * 3600 * 1000   # re-check GitHub for a new release

# How long after a match to ask OpenDota for its game mode. Valve publishes
# matches a few minutes after they end; bot/lobby games never appear.
MODE_DELAYS = [120, 600, 1800, 7200, 21600]

LIVE_STATES = ("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
               "DOTA_GAMERULES_STATE_PRE_GAME")


# ---------------------------------------------------------------------------
# settings and formatting
# ---------------------------------------------------------------------------

def load_settings():
    settings = setup_gsi.ensure_settings()
    if settings.get("recap_mode") not in ("popup", "panel"):
        settings["recap_mode"] = "popup"
    if not isinstance(settings.get("turbo_only"), bool):
        settings["turbo_only"] = False
    if settings.get("tips") not in ("off", "game", "second"):
        settings["tips"] = "game"
    if settings.get("tips_size") not in ("full", "small"):
        settings["tips_size"] = "full"
    return settings


def save_settings(settings):
    """Write to a temp file then swap it in, so a crash can't half-write."""
    LOCAL.mkdir(exist_ok=True)
    tmp = SETTINGS.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    os.replace(tmp, SETTINGS)


def fmt_duration(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_when(ts):
    when = datetime.fromtimestamp(ts)
    today = datetime.now().date()
    if when.date() == today:
        return f"Today {when:%H:%M}"
    if when.date() == today - timedelta(days=1):
        return f"Yesterday {when:%H:%M}"
    return f"{when:%d %b %H:%M}"


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def mode_label(row):
    if row["game_mode"] is not None:
        return opendota.MODE_NAMES.get(row["game_mode"],
                                       f"Mode {row['game_mode']}")
    if row["mode_status"] == "not_public":
        return "Practice / lobby"
    return "Checking mode..."


def pct(wins, losses):
    total = wins + losses
    return round(100 * wins / total) if total else None


def streaks(rows):
    """(current streak text, colour key, best win streak) from newest-first
    rows."""
    results = [r["won"] for r in rows if r["won"] in (0, 1)]
    if not results:
        return "-", None, 0
    first, n = results[0], 0
    for r in results:
        if r != first:
            break
        n += 1
    best = run = 0
    for r in results:
        run = run + 1 if r == 1 else 0
        best = max(best, run)
    return f"{'W' if first else 'L'}{n}", first, best


# ---------------------------------------------------------------------------
# GSI listener (background thread -> queue -> Qt thread)
# ---------------------------------------------------------------------------

def start_listener(port, token, inbox):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return
            if (data.get("auth") or {}).get("token") != token:
                self.send_response(403)   # not from our Dota config
                self.end_headers()
                return
            data.pop("auth", None)
            inbox.put(("gsi", data))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------------------------------------------------------------------------
# controller
# ---------------------------------------------------------------------------

class Controller:
    def __init__(self, app):
        self.app = app
        LOCAL.mkdir(parents=True, exist_ok=True)
        PORTRAITS.mkdir(exist_ok=True)
        self.settings = load_settings()
        self.store = Store(DB_PATH)
        self.watcher = MatchWatcher()
        self.inbox = queue.Queue()
        self.heroes = self._load_hero_cache()
        self.pixmaps = {}
        self.downloading = set()
        self.last_message = 0.0
        self.mode_in_flight = set()
        self.card = None
        self.card_match = None
        self.card_hero = None
        self.panel = None
        self.panel_idle = ("Today 0-0", "no games yet", ui.MUTED, ui.ACCENT)
        self.listen_error = None
        self.server = None
        self._repaired = False
        self.update = None          # (version, url) of a newer release
        self.version = __version__

        try:
            self.server = start_listener(self.settings["port"],
                                         self.settings["token"], self.inbox)
        except OSError as err:
            self.listen_error = (f"Couldn't listen on port "
                                 f"{self.settings['port']} ({err}). Is another "
                                 "copy of Turbo Tracker or capture.py running?")

        self.window = ui.MainWindow(self)
        self.window.closed.connect(self.on_window_closed)
        if not self.heroes or not all(isinstance(v, dict)
                                      for v in self.heroes.values()):
            threading.Thread(target=self._fetch_heroes, daemon=True).start()

        # Tray icon: the way back to the window after closing it.
        self.tray = None
        self._tray_tip = None

        # Tips card while dead / paused, fed by OpenDota item popularity.
        self.tips = ui.TipsCard(self.item_icon)
        self.tips.set_compact(self.settings["tips_size"] == "small")
        self.toast = ui.ItemToast(self.item_icon)
        self.owned_seen = (None, set())     # (match id, items last seen)
        self.items_db = None
        self.pops = {}              # hero id -> item popularity
        self.pop_fetching = set()
        self.pop_failed = set()
        self.tips_preview_until = 0.0
        threading.Thread(target=lambda: self.inbox.put(
            ("itemsdb", builds.load_items(LOCAL / "items.json"))),
            daemon=True).start()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = ui.Tray(self.show_window, self.show_last_recap,
                                self.quit)
            self.tray.show()
        # A second launch (Start menu, desktop) asks this copy to show up.
        self.instance_server = QLocalServer(app)
        self.instance_server.newConnection.connect(self._second_launch)
        QLocalServer.removeServer(INSTANCE)
        self.instance_server.listen(INSTANCE)

        self.refresh()
        self.apply_recap_mode()
        self.window.show()

        self._timer(150, self._poll)
        self._timer(30000, self._check_modes, first=3000)
        self._timer(2000, self._pin)
        self._timer(UPDATE_EVERY_MS, self._check_update, first=5000)

    def _timer(self, interval, fn, first=None):
        t = QTimer(self.app)
        t.timeout.connect(fn)
        t.start(interval)
        if first is not None:
            QTimer.singleShot(first, fn)
        return t

    # --- heroes: names and portraits ------------------------------------

    def _load_hero_cache(self):
        try:
            data = json.loads(HEROES_CACHE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _fetch_heroes(self):
        try:
            self.inbox.put(("heroes", opendota.hero_names()))
        except Exception:
            pass

    def hero_name(self, internal):
        info = self.heroes.get(internal or "")
        if isinstance(info, dict):
            return info.get("name") or internal
        if isinstance(info, str):          # older cache format
            return info
        if not internal:
            return "Unknown hero"
        return internal.replace("npc_dota_hero_", "").replace("_", " ").title()

    def portrait(self, internal):
        """QPixmap for a hero, or None while it downloads."""
        if not internal:
            return None
        info = self.heroes.get(internal)
        url = info.get("img") if isinstance(info, dict) else None
        path = PORTRAITS / f"{internal.replace('npc_dota_hero_', '')}.png"
        return self._cached_pixmap(internal, path, url)

    def item_icon(self, item):
        """QPixmap for an item dict from builds, or None while it downloads."""
        key = item.get("key") or ""
        return self._cached_pixmap("item:" + key, LOCAL / "items" / f"{key}.png",
                                   item.get("img"))

    def _cached_pixmap(self, cache_key, path, url):
        if cache_key in self.pixmaps:
            return self.pixmaps[cache_key]
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.pixmaps[cache_key] = pix
                return pix
        if url and cache_key not in self.downloading:
            self.downloading.add(cache_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            threading.Thread(target=self._download,
                             args=(cache_key, url, path), daemon=True).start()
        return None

    def _download(self, internal, url, path):
        try:
            data = opendota.download(url)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except Exception:
            pass
        self.inbox.put(("portrait", internal))

    # --- screen updates --------------------------------------------------

    def refresh(self):
        turbo = self.settings["turbo_only"]
        rows = self.store.matches(turbo)
        s = self.store.summary(turbo)
        tw, tl = self.store.today_record(turbo)
        w = self.window

        w.t_games.set(str(s["games"]), f"{s['today']} today  ·  {tw}-{tl}")
        w.t_record.set(f"{s['wins']} - {s['losses']}")
        w.t_record.bar.set(s["wins"], s["losses"])
        w.t_record.sub.setText("")
        rate = pct(s["wins"], s["losses"])
        last10 = [r["won"] for r in rows[:10] if r["won"] in (0, 1)]
        w.t_rate.set("-" if rate is None else f"{rate}%",
                     f"Last {len(last10)}: {sum(last10)}-"
                     f"{len(last10) - sum(last10)}" if last10 else "",
                     ui.TEXT if rate is None else
                     (ui.WIN if rate >= 50 else ui.LOSS))
        text, key, best = streaks(rows)
        w.t_streak.set(text, f"Best win streak: {best}" if best else "",
                       {1: ui.WIN, 0: ui.LOSS}.get(key, ui.TEXT))

        w.matches.set_rows([self._match_row(r) for r in rows], (
            "No Turbo games confirmed yet.\n\nGames appear here once OpenDota "
            "confirms their mode. Bot and lobby games never do - pick "
            "\"All games\" to see everything." if turbo else
            "No games yet.\n\nLeave Turbo Tracker running and play a match - "
            "it shows up here the moment the game ends."))
        w.heroes.set_rows([self._hero_row(h) for h in self.store.heroes(turbo)],
                          "Your heroes will appear here after your first game.")
        self.update_banner()
        self.update_panel()

    def _match_row(self, r):
        return {
            "hero_internal": r["hero_internal"],
            "hero": self.hero_name(r["hero_internal"]),
            "subtitle": f"{fmt_when(r['ended_at'])}  ·  {mode_label(r)}",
            "won": r["won"],
            "kda": f"{r['kills']} / {r['deaths']} / {r['assists']}",
            "length": fmt_duration(r["duration"]),
            "gpm": r["gpm"], "xpm": r["xpm"],
            "lh": f"{r['last_hits']} / {r['denies']}",
        }

    def _hero_row(self, h):
        wins, losses = h["wins"] or 0, h["losses"] or 0
        return {
            "hero_internal": h["hero_internal"],
            "hero": self.hero_name(h["hero_internal"]),
            "subtitle": f"Last played {fmt_when(h['last_played'])}",
            "games": h["games"], "record": f"{wins} - {losses}",
            "rate": pct(wins, losses),
            "kda": f"{h['k']:.1f} / {h['d']:.1f} / {h['a']:.1f}",
            "gpm": round(h["gpm"] or 0),
        }

    def update_banner(self):
        text, button = None, False
        if self.listen_error:
            text = self.listen_error
        elif time.time() - self.last_message < 60:
            text = None          # data is arriving, so the setup works
        else:
            cfg = setup_gsi.config_path()
            if cfg is None:
                text = "Couldn't find Dota 2 in your Steam libraries."
            elif not cfg.exists():
                text = ("Dota isn't connected to Turbo Tracker yet. Click "
                        "Set up now to add the connection file.")
                button = True
            elif not setup_gsi.config_matches() and not self._repaired:
                # Our file, written by another copy (source vs exe) with a
                # different token: rewrite it once, quietly.
                self._repaired = True
                try:
                    setup_gsi.install()
                    text = ("Updated Dota's connection file for this copy of "
                            "Turbo Tracker - restart Dota if it's open.")
                except RuntimeError as err:
                    text = str(err)
            elif setup_gsi.launch_option_set() is False:
                text = ("One step left: in Steam, right-click Dota 2 › "
                        "Properties › General › Launch Options and "
                        "add  -gamestateintegration  then restart Dota.")
        self.window.set_banner(text, button)

    def run_setup(self):
        try:
            setup_gsi.install()
        except RuntimeError as err:
            self.window.set_banner(str(err), False)
            return
        self.update_banner()

    def update_status(self):
        live = self.watcher.status()
        recent = time.time() - self.last_message < 45
        if self.listen_error:
            color, text = ui.LOSS, "Not listening"
        elif live and recent and live["state"] in LIVE_STATES:
            bits = [self.hero_name(live["hero_internal"]),
                    fmt_duration(live["clock"]),
                    f"{live['kills']}/{live['deaths']}/{live['assists']}",
                    f"{live['gpm']} GPM"]
            if not live["alive"]:
                bits.append(f"respawn {live['respawn']}s")
            color, text = ui.WIN, "In game  ·  " + "  ·  ".join(bits)
        elif live and recent:
            color, text = ui.ACCENT, "Match loading"
        elif recent:
            color, text = ui.ACCENT, "Dota is running · waiting for a match"
        else:
            color, text = ui.SUBTLE, "Waiting for Dota"
        self.window.status.set(color, text)
        self.update_tips(live, recent)
        if self.tray and text != self._tray_tip:
            self._tray_tip = text
            self.tray.setToolTip(("Turbo Tracker\n" + text)[:127])
        if self.panel:
            if live and recent and live["state"] in LIVE_STATES:
                self.panel.show_text(
                    fmt_duration(live["clock"]),
                    f"{self.hero_name(live['hero_internal'])}  "
                    f"{live['kills']}/{live['deaths']}/{live['assists']}",
                    ui.TEXT, ui.WIN)
            else:
                self.panel.show_text(*self.panel_idle)

    # --- message loop ----------------------------------------------------

    def _poll(self):
        changed = repaint = False
        try:
            while True:
                kind, payload = self.inbox.get_nowait()
                if kind == "gsi":
                    first = time.time() - self.last_message > 60
                    self.last_message = time.time()
                    if first:
                        self.update_banner()
                    match = self.watcher.feed(payload)
                    self._check_new_items()
                    if match and self.store.add_match(match):
                        changed = True
                        self.show_recap(match["match_id"])
                elif kind == "heroes":
                    self.heroes = payload
                    try:
                        HEROES_CACHE.write_text(json.dumps(payload),
                                                encoding="utf-8")
                    except OSError:
                        pass
                    changed = True
                elif kind == "portrait":
                    self.downloading.discard(payload)
                    repaint = True
                    if self.card and self.card_hero == payload:
                        self.card.set_pixmap(self.portrait(payload))
                    if payload.startswith("item:"):
                        if self.tips.isVisible():
                            self.tips.refresh_icons()
                        self.toast.refresh_icons()
                elif kind == "itemsdb":
                    self.items_db = payload
                elif kind == "pop":
                    hero_id, data = payload
                    self.pop_fetching.discard(hero_id)
                    if data:
                        self.pops[hero_id] = data
                    else:
                        self.pop_failed.add(hero_id)
                elif kind == "update":
                    self._update_result(payload)
                elif kind == "mode":
                    self._mode_result(*payload)
                    changed = True
        except queue.Empty:
            pass
        if changed:
            self.refresh()
        elif repaint:
            self.window.matches.repaint_rows()
            self.window.heroes.repaint_rows()
        self.update_status()

    # --- tips card while dead / paused -----------------------------------

    def _want_pop(self, hero_id):
        """Start fetching a hero's item popularity (once) so it's ready by
        the time they die."""
        if not hero_id or hero_id in self.pops or hero_id in self.pop_fetching:
            return
        self.pop_fetching.add(hero_id)
        self.pop_failed.discard(hero_id)
        folder = LOCAL / "itempop"
        threading.Thread(target=lambda: self.inbox.put(
            ("pop", (hero_id, builds.load_popularity(hero_id, folder)))),
            daemon=True).start()

    def update_tips(self, live, recent):
        """Show the card only while dead or paused; hide it the moment
        that stops (respawn, buyback, unpause, game over)."""
        where = self.settings["tips"]
        if live and recent:
            self._want_pop(live.get("hero_id"))
        in_game = bool(live and recent and live["state"] == LIVE_STATES[0])
        waiting = in_game and (not live["alive"] or live.get("paused"))
        preview = time.time() < self.tips_preview_until
        if where == "off" or not (waiting or preview):
            if self.tips.isVisible():
                self.tips.hide()
            return
        if not waiting:
            live = self._preview_live()
        hero_id = live.get("hero_id")
        rec = builds.recommend(self.pops.get(hero_id), self.items_db,
                               live["clock"], live.get("owned") or set())
        message = None
        if rec is None:
            message = ("Item builds unavailable - are you offline?"
                       if hero_id in self.pop_failed else
                       "Loading item builds...")
        if live.get("paused"):
            self.tips.set_headline("\u23f8  GAME PAUSED", ui.ACCENT)
        elif live["respawn"] > 0:
            self.tips.set_headline(f"RESPAWN IN {live['respawn']}s", ui.LOSS)
        else:
            self.tips.set_headline("YOU'RE DEAD", ui.LOSS)
        context = (f"{self.hero_name(live['hero_internal'])}  \u00b7  "
                   f"{fmt_duration(live['clock'])}")
        if not waiting:
            context += "  \u00b7  preview"
        before = self.tips.size()
        self.tips.set_content(context, rec, message)
        if not self.tips.isVisible() or self.tips.size() != before:
            self.tips.place(where)
        if not self.tips.isVisible():
            self.tips.show()
            winutil.pin_topmost(int(self.tips.winId()))

    def _check_new_items(self):
        """After each Dota message: did you just finish an item? The first
        look at a match only records what you have, so opening the app
        mid-game doesn't announce your whole inventory."""
        live = self.watcher.status()
        if not live or live["state"] != LIVE_STATES[0]:
            return
        owned = set(live.get("owned") or ())
        match_id, before = self.owned_seen
        self.owned_seen = (live["match_id"], owned)
        if match_id != live["match_id"] or self.settings["tips"] == "off":
            return
        new = [k for k in owned - before
               if builds.is_finished(k, self.items_db)]
        if not new:
            return
        by_key = {it["key"]: it for it in (self.items_db or {}).values()}
        item = by_key[new[0]]
        rec = builds.recommend(self.pops.get(live.get("hero_id")),
                               self.items_db, live["clock"], owned)
        self.toast.show_item(item, builds.next_buys(rec, 3),
                             self.settings["tips"])

    def _preview_live(self):
        """Stand-in game state for the preview shown when you pick a tips
        option: your last hero, dead at 10:00."""
        last = self.store.matches(limit=1)
        hero, hero_id = ("npc_dota_hero_pudge", 14)
        if last and last[0]["hero_id"]:
            hero, hero_id = last[0]["hero_internal"], last[0]["hero_id"]
        self._want_pop(hero_id)
        return {"hero_internal": hero, "hero_id": hero_id, "clock": 600,
                "alive": False, "respawn": 23, "paused": False,
                "owned": set(), "state": LIVE_STATES[0]}

    def set_tips_size(self, key):
        self.settings["tips_size"] = key
        save_settings(self.settings)
        self.tips.hide()
        self.tips.set_compact(key == "small")
        if self.settings["tips"] != "off":
            self.tips_preview_until = time.time() + 6
        self.update_status()

    def set_tips(self, key):
        self.settings["tips"] = key
        save_settings(self.settings)
        self.tips.hide()
        self.toast.hide()
        # Show where it will appear for a few seconds.
        self.tips_preview_until = time.time() + 6 if key != "off" else 0
        self.update_status()

    # --- update check ---------------------------------------------------

    def _check_update(self):
        threading.Thread(target=lambda: self.inbox.put(
            ("update", updates.latest_release())), daemon=True).start()

    def _update_result(self, result):
        if not result:
            return                      # offline or GitHub hiccup: try later
        version, url = result
        if (updates.is_newer(version, __version__)
                and self.settings.get("skip_update") != version):
            self.update = (version, url)
        else:
            self.update = None
        self._show_update()

    def _show_update(self):
        version = self.update[0] if self.update else None
        self.window.set_update(version, __version__)
        if self.panel:
            self.panel.set_update(version, self.open_update)
        if self.tray:
            self.tray.set_update(version, self.open_update)

    def open_update(self):
        if self.update:
            QDesktopServices.openUrl(QUrl(self.update[1]))

    def skip_update(self):
        """Later: stay quiet about this version (a newer one still shows)."""
        if self.update:
            self.settings["skip_update"] = self.update[0]
            save_settings(self.settings)
        self.update = None
        self._show_update()

    # --- OpenDota game-mode lookups --------------------------------------

    def _check_modes(self):
        now = time.time()
        for row in self.store.pending_modes():
            mid, tries = row["match_id"], row["mode_tries"]
            if mid in self.mode_in_flight:
                continue
            if tries >= len(MODE_DELAYS):
                self.store.set_mode(mid, None, "not_public")
                self.refresh()
            elif now >= row["ended_at"] + MODE_DELAYS[tries]:
                self.mode_in_flight.add(mid)
                threading.Thread(target=self._lookup_mode, args=(mid,),
                                 daemon=True).start()

    def _lookup_mode(self, match_id):
        status, mode = opendota.match_mode(match_id)
        self.inbox.put(("mode", (match_id, status, mode)))

    def _mode_result(self, match_id, status, mode):
        self.mode_in_flight.discard(match_id)
        if status == "found":
            self.store.set_mode(match_id, mode, "found")
        else:
            self.store.note_mode_try(match_id)
            row = self.store.get(match_id)
            if row and row["mode_tries"] >= len(MODE_DELAYS):
                self.store.set_mode(match_id, None, "not_public")
        if self.card and self.card_match == match_id:
            self.card.set_mode(mode_label(self.store.get(match_id)))

    # --- recap card ------------------------------------------------------

    def recap_info(self, row):
        hero = self.hero_name(row["hero_internal"])
        facts = self.store.hero_facts(row["hero_internal"])
        record = f"{facts['wins']}-{facts['losses']} all-time on this hero"
        if row["ended_at"] >= start_of_today():
            fact = f"{ordinal(facts['today'])} game on {hero} today · {record}"
        else:
            fact = f"Played {fmt_when(row['ended_at'])} · {record}"
        tw, tl = self.store.today_record()
        return {
            "result": {1: "VICTORY", 0: "DEFEAT"}.get(row["won"], "GAME OVER"),
            "color": {1: ui.WIN, 0: ui.LOSS}.get(row["won"], ui.ACCENT),
            "hero": hero,
            "length": fmt_duration(row["duration"]),
            "kda_parts": (row["kills"], row["deaths"], row["assists"]),
            "chips": [f"{row['gpm']} GPM", f"{row['xpm']} XPM",
                      f"{row['last_hits']} LH", f"Lvl {row['level']}"],
            "fact": fact,
            "today": f"Today  {tw} - {tl}",
            "mode": mode_label(row),
        }

    def show_recap(self, match_id):
        row = self.store.get(match_id)
        if row is None:
            return
        self.close_card()
        panel_mode = self.settings["recap_mode"] == "panel"
        self.card = ui.RecapCard(self.recap_info(row),
                                 self.portrait(row["hero_internal"]),
                                 self._card_closed,
                                 anchor=self.panel if panel_mode else None,
                                 timeout=None if panel_mode else 20)
        self.card_match = match_id
        self.card_hero = row["hero_internal"]

    def _card_closed(self, card):
        if self.card is card:
            self.card = None
            self.card_match = None

    def close_card(self):
        if self.card:
            self.card.dismiss()

    def show_last_recap(self):
        rows = self.store.matches(limit=1)
        if rows:
            self.show_recap(rows[0]["match_id"])

    # --- panel mode ------------------------------------------------------

    def apply_recap_mode(self):
        if self.settings["recap_mode"] == "panel":
            if not self.panel:
                self.panel = ui.TaskbarPanel(
                    self.show_window, self.show_last_recap, self.quit,
                    saved_pos=self.settings.get("panel_pos"),
                    on_moved=self._panel_moved)
                self._show_update()
            self.update_panel()
        elif self.panel:
            self.panel.close()
            self.panel.deleteLater()
            self.panel = None

    def update_panel(self):
        if not self.panel:
            return
        turbo = self.settings["turbo_only"]
        tw, tl = self.store.today_record(turbo)
        last = self.store.matches(turbo, limit=1)
        if last:
            r = last[0]
            res = {1: "W", 0: "L"}.get(r["won"], "?")
            color = {1: ui.WIN, 0: ui.LOSS}.get(r["won"], ui.MUTED)
            tail = (f"{self.hero_name(r['hero_internal'])} {res}  "
                    f"{r['kills']}/{r['deaths']}/{r['assists']}")
        else:
            color, tail = ui.MUTED, "no games yet"
        self.panel_idle = (f"Today {tw}-{tl}", tail, color, ui.ACCENT)
        self.update_status()

    def _panel_moved(self, pos):
        """The panel was dragged (pos = [centre x, top y]) or reset (None)."""
        if pos is None:
            self.settings.pop("panel_pos", None)
        else:
            self.settings["panel_pos"] = list(pos)
        save_settings(self.settings)

    def _pin(self):
        # Skip while the panel's menu is open, or the pin buries it (bug #4),
        # and mid-drag.
        if self.panel and not self.panel.menu_open and not self.panel.dragging:
            winutil.pin_topmost(int(self.panel.winId()))
        if self.card:
            winutil.pin_topmost(int(self.card.winId()))
        if self.tips.isVisible():
            winutil.pin_topmost(int(self.tips.winId()))
        if self.toast.isVisible():
            winutil.pin_topmost(int(self.toast.winId()))

    # --- options and lifetime ---------------------------------------------

    def set_filter(self, key):
        self.settings["turbo_only"] = key == "turbo"
        save_settings(self.settings)
        self.refresh()

    def set_recap_mode(self, key):
        self.settings["recap_mode"] = key
        save_settings(self.settings)
        self.close_card()
        self.apply_recap_mode()

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _second_launch(self):
        conn = self.instance_server.nextPendingConnection()
        if conn:
            conn.disconnectFromServer()
        self.show_window()

    def on_window_closed(self):
        # Keep running (it has games to log): hide to the tray or panel.
        if not self.tray and not self.panel:
            self.quit()        # no tray on this system: nowhere to hide
            return
        self.window.hide()
        if self.tray and not self.panel and                 not self.settings.get("tray_hint_shown"):
            self.tray.showMessage(
                "Turbo Tracker is still running",
                "It keeps logging your games. Click the Turbo Tracker icon "
                "in the tray (under ^ if it's hidden) to open it again, or "
                "right-click it > Quit.",
                ui.app_icon(), 8000)
            self.settings["tray_hint_shown"] = True
            save_settings(self.settings)

    def quit(self):
        self.quitting = True
        if self.tray:
            self.tray.hide()      # or a dead icon lingers until hovered
        self.tips.hide()
        if self.server:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        # exit() rather than quit(): Qt 6's quit() first asks every window
        # to close and silently gives up if one says no.
        self.app.exit(0)


def main():
    app = QApplication(sys.argv)
    if not acquire():
        return
    app.setApplicationName("Turbo Tracker")
    app.setQuitOnLastWindowClosed(False)
    ui.apply_theme(app)
    ctl = Controller(app)   # noqa: F841 - keeps everything alive
    sys.exit(app.exec())


def acquire():
    """True if we're the only copy. Otherwise ask the running copy to show
    its window (so opening the app again from the Start menu just brings
    it back) and bow out."""
    if winutil.acquire_single_instance("Local\\" + INSTANCE):
        return True
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE)
    if sock.waitForConnected(1500):
        sock.disconnectFromServer()
        return False
    winutil.message_box("Turbo Tracker is already running.", "Turbo Tracker")
    return False


if __name__ == "__main__":
    main()
