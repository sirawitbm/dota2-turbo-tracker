"""SQLite storage: one row per match."""

import sqlite3
import time
from datetime import datetime

TURBO = 23

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id      TEXT PRIMARY KEY,
    ended_at      INTEGER NOT NULL,   -- unix seconds
    hero_id       INTEGER,
    hero_internal TEXT,               -- e.g. npc_dota_hero_furion
    won           INTEGER,            -- 1 win, 0 loss, NULL unknown
    team          TEXT,
    duration      INTEGER,            -- in-game seconds (clock time)
    level         INTEGER,
    kills         INTEGER,
    deaths        INTEGER,
    assists       INTEGER,
    last_hits     INTEGER,
    denies        INTEGER,
    gpm           INTEGER,
    xpm           INTEGER,
    radiant_score INTEGER,
    dire_score    INTEGER,
    items         TEXT,               -- JSON list of item names
    game_mode     INTEGER,            -- from OpenDota; 23 = Turbo
    mode_status   TEXT DEFAULT 'pending', -- pending / found / not_public
    mode_tries    INTEGER DEFAULT 0,
    source        TEXT DEFAULT 'gsi'
);
"""

COLUMNS = ["match_id", "ended_at", "hero_id", "hero_internal", "won", "team",
           "duration", "level", "kills", "deaths", "assists", "last_hits",
           "denies", "gpm", "xpm", "radiant_score", "dire_score", "items"]


def start_of_today():
    now = datetime.now()
    return int(datetime(now.year, now.month, now.day).timestamp())


class Store:
    def __init__(self, path):
        # Used from the Tk thread only; lookups hand results back via a queue.
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def add_match(self, match):
        """Save a finished match. Returns False if it was already saved."""
        values = [match.get(c) for c in COLUMNS]
        cur = self.db.execute(
            f"INSERT OR IGNORE INTO matches ({','.join(COLUMNS)}) "
            f"VALUES ({','.join('?' * len(COLUMNS))})", values)
        self.db.commit()
        return cur.rowcount == 1

    def set_mode(self, match_id, game_mode, status):
        self.db.execute(
            "UPDATE matches SET game_mode=?, mode_status=?, "
            "mode_tries=mode_tries+1 WHERE match_id=?",
            (game_mode, status, match_id))
        self.db.commit()

    def note_mode_try(self, match_id):
        self.db.execute("UPDATE matches SET mode_tries=mode_tries+1 "
                        "WHERE match_id=?", (match_id,))
        self.db.commit()

    def pending_modes(self, max_age_days=3):
        since = int(time.time()) - max_age_days * 86400
        return self.db.execute(
            "SELECT match_id, ended_at, mode_tries FROM matches "
            "WHERE mode_status='pending' AND ended_at>=?", (since,)).fetchall()

    # --- reading ---------------------------------------------------------

    @staticmethod
    def _where(turbo_only):
        return f"WHERE game_mode={TURBO}" if turbo_only else ""

    def matches(self, turbo_only=False, limit=500):
        return self.db.execute(
            f"SELECT * FROM matches {self._where(turbo_only)} "
            "ORDER BY ended_at DESC LIMIT ?", (limit,)).fetchall()

    def summary(self, turbo_only=False):
        row = self.db.execute(
            "SELECT COUNT(*) games, SUM(won=1) wins, SUM(won=0) losses, "
            f"SUM(ended_at>=?) today FROM matches {self._where(turbo_only)}",
            (start_of_today(),)).fetchone()
        return {k: row[k] or 0 for k in row.keys()}

    def today_record(self, turbo_only=False):
        where = "WHERE ended_at>=?" + (f" AND game_mode={TURBO}"
                                       if turbo_only else "")
        row = self.db.execute(
            f"SELECT SUM(won=1) w, SUM(won=0) l FROM matches {where}",
            (start_of_today(),)).fetchone()
        return row["w"] or 0, row["l"] or 0

    def heroes(self, turbo_only=False):
        return self.db.execute(
            "SELECT hero_id, hero_internal, COUNT(*) games, "
            "SUM(won=1) wins, SUM(won=0) losses, "
            "AVG(kills) k, AVG(deaths) d, AVG(assists) a, AVG(gpm) gpm, "
            "MAX(ended_at) last_played "
            f"FROM matches {self._where(turbo_only)} "
            "GROUP BY hero_internal ORDER BY games DESC, wins DESC"
        ).fetchall()

    def hero_facts(self, hero_internal):
        """Numbers for the recap card: today's count and overall record."""
        row = self.db.execute(
            "SELECT SUM(ended_at>=?) today, SUM(won=1) wins, "
            "SUM(won=0) losses FROM matches WHERE hero_internal=?",
            (start_of_today(), hero_internal)).fetchone()
        return {k: row[k] or 0 for k in row.keys()}

    def get(self, match_id):
        return self.db.execute("SELECT * FROM matches WHERE match_id=?",
                               (match_id,)).fetchone()
