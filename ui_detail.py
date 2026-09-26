"""The match report page: open a match from the Matches list.

Shows the after-game damage report (from OpenDota's parsed replay) and
what the app saw live (death recaps, time spent disabled).
"""

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

import ui
from ui import (BORDER, LOSS, MUTED, SUBTLE, SURFACE_2, TEXT, WIN, button,
                card, draw_pill, draw_portrait, font, label, tint)

TYPE_COLORS = {"Physical": "#e5605a", "Magical": "#5b9cf5",
               "Pure": "#f5c542", "Other": "#8b93a5"}


def fmt_clock(seconds):
    seconds = int(seconds or 0)
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{seconds // 60}:{seconds % 60:02d}"


class TypeBar(QWidget):
    """One rounded bar split by damage type."""

    def __init__(self, by_type):
        super().__init__()
        self.by_type = by_type
        self.setFixedHeight(14)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        total = sum(self.by_type.values()) or 1
        from PySide6.QtGui import QPainterPath
        clip = QPainterPath()
        clip.addRoundedRect(r, 7, 7)
        p.setClipPath(clip)
        p.fillRect(r, QColor(BORDER))
        x = r.left()
        for t, amount in self.by_type.items():
            w = r.width() * amount / total
            if w > 0:
                p.fillRect(QRectF(x, r.top(), w, r.height()),
                           QColor(TYPE_COLORS[t]))
                x += w


class SplitBar(QWidget):
    """Damage from one hero: spells (bright) + attacks & items (dim)."""

    def __init__(self, spells, attacks, scale):
        super().__init__()
        self.spells, self.attacks, self.scale = spells, attacks, scale or 1
        self.setFixedHeight(8)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(r, 4, 4)
        ws = r.width() * self.spells / self.scale
        wa = r.width() * self.attacks / self.scale
        p.setBrush(QColor("#b48cf2"))
        p.drawRoundedRect(QRectF(r.left(), r.top(), max(ws, 0), r.height()), 4, 4)
        p.setBrush(tint("#e5605a", 200))
        p.drawRoundedRect(QRectF(r.left() + ws, r.top(), max(wa, 0), r.height()),
                          4, 4)


class Portrait(QWidget):
    def __init__(self, pix, name, size):
        super().__init__()
        self.pix, self.name = pix, name
        self.setFixedSize(size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        draw_portrait(p, self.rect(), self.pix, self.name, radius=6)


def caption(text):
    c = label(text.upper(), "caption")
    return c


def small(text, color=MUTED, size=12):
    l = label(text)
    l.setStyleSheet(f"color: {color}; font-size: {size}px;")
    l.setWordWrap(True)
    return l


def nowrap(text, color=TEXT, size=12):
    l = small(text, color, size)
    l.setWordWrap(False)
    return l


class MatchDetail(QWidget):
    def __init__(self, ctl, on_back):
        super().__init__()
        self.ctl = ctl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(button("←  Back to matches", "ghost", on_back))
        top.addStretch()
        outer.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        outer.addWidget(self.scroll, 1)
        self.match_id = None

    def show_match(self, row, status, report, extras):
        """row: sqlite Row from matches; status/report from store.report()."""
        self.match_id = row["match_id"]
        ctl = self.ctl
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 8, 8, 16)
        lay.setSpacing(14)

        # -- header -----------------------------------------------------
        head = card()
        h = QHBoxLayout(head)
        h.setContentsMargins(18, 16, 18, 16)
        h.setSpacing(16)
        hero = ctl.hero_name(row["hero_internal"])
        h.addWidget(Portrait(ctl.portrait(row["hero_internal"]), hero,
                             QSize(128, 72)))
        t = QVBoxLayout()
        t.setSpacing(2)
        name = label(hero, "title")
        t.addWidget(name)
        result = {1: ("VICTORY", WIN), 0: ("DEFEAT", LOSS)}.get(
            row["won"], ("RESULT UNKNOWN", MUTED))
        res = label(result[0])
        res.setStyleSheet(f"color: {result[1]}; font-size: 13px; font-weight: 700;")
        t.addWidget(res)
        t.addWidget(small(
            f"{row['kills']} / {row['deaths']} / {row['assists']}   ·   "
            f"{fmt_clock(row['duration'])}   ·   {ctl.when(row['ended_at'])}"
            f"   ·   {ctl.mode_text(row)}", TEXT, 13))
        h.addLayout(t, 1)
        lay.addWidget(head)

        # -- damage report ------------------------------------------------
        dmg = card()
        d = QVBoxLayout(dmg)
        d.setContentsMargins(18, 16, 18, 18)
        d.setSpacing(10)
        if report:
            row_ = QHBoxLayout()
            row_.addWidget(caption("Damage you took"))
            row_.addStretch()
            total = label(f"{report['total']:,}")
            total.setStyleSheet("font-size: 22px; font-weight: 700;")
            row_.addWidget(total)
            d.addLayout(row_)
            d.addWidget(TypeBar(report["by_type"]))
            legend = QHBoxLayout()
            tot = report["total"] or 1
            for kind, amount in report["by_type"].items():
                if amount:
                    legend.addWidget(nowrap(
                        f"<span style='color:{TYPE_COLORS[kind]}'>■</span> "
                        f"{kind}  <b>{round(100 * amount / tot)}%</b>  "
                        f"({amount:,})", TEXT, 12))
            legend.addStretch()
            d.addLayout(legend)

            d.addSpacing(6)
            d.addWidget(caption("From enemy heroes"))
            scale = max((x["total"] for x in report["by_hero"]), default=1)
            for x in report["by_hero"]:
                d.addLayout(self._hero_row(x, scale))
            if report["other"]:
                d.addWidget(small(f"Creeps, towers & summons: "
                                  f"{report['other']:,}"))
            d.addWidget(small("<span style='color:#b48cf2'>■</span> spells"
                              "   <span style='color:#e5605a'>■</span> "
                              "attacks & items", SUBTLE, 11))

            d.addSpacing(6)
            d.addWidget(caption("Spells & items that hit you"))
            for s in report["spells"][:10]:
                d.addLayout(self._spell_row(s))
        else:
            d.addWidget(caption("Damage you took"))
            d.addWidget(small({
                "pending": "Waiting for OpenDota to analyse this game's "
                           "replay - usually 5 to 15 minutes after it ends. "
                           "You'll get a notice when the report is ready.",
                "unavailable": "No damage report for this game. Bot and "
                               "lobby games can't be analysed, and now and "
                               "then OpenDota can't get a replay.",
            }.get(status, "No damage report for this game - it was played "
                          "before this version of Turbo Tracker."), TEXT, 13))
        lay.addWidget(dmg)

        # -- deaths -------------------------------------------------------
        deaths = self._deaths(report, extras)
        dc = card()
        dl = QVBoxLayout(dc)
        dl.setContentsMargins(18, 16, 18, 18)
        dl.setSpacing(10)
        dl.addWidget(caption(f"Deaths ({len(deaths)})"))
        if not deaths:
            dl.addWidget(small("No deaths recorded." if row["deaths"] == 0
                               else "Deaths weren't recorded for this game."))
        for i, (time_, killer, recap) in enumerate(deaths, 1):
            line = QHBoxLayout()
            line.setSpacing(10)
            line.addWidget(small(f"<b>Death {i}</b>  ·  "
                                 f"{fmt_clock(time_)}", TEXT, 13))
            if killer:
                kname = ctl.hero_name(killer)
                line.addWidget(small("killed by", MUTED, 12))
                line.addWidget(Portrait(ctl.portrait(killer), kname,
                                        QSize(40, 23)))
                line.addWidget(small(kname, TEXT, 13))
            line.addStretch()
            if recap:
                line.addWidget(small(
                    f"full HP → dead in {recap['window']:.1f}s"
                    if recap["from_pct"] >= 95 else
                    f"from {recap['from_pct']}% → dead in "
                    f"{recap['window']:.1f}s"))
            dl.addLayout(line)
            if recap:
                dl.addWidget(ui.HpGraph(recap))
                bits = [f"<span style='color:{ui.CONTROL_COLORS[c]}'>■"
                        f"</span> {c.capitalize()} {v:.1f}s"
                        for c, v in recap["controls"].items()]
                dl.addWidget(small("   ".join(bits) if bits else
                                   "No disables before this death", MUTED, 12))
        lay.addWidget(dc)

        # -- disables ------------------------------------------------------
        dis = card()
        xl = QVBoxLayout(dis)
        xl.setContentsMargins(18, 16, 18, 18)
        xl.addWidget(caption("Time you spent disabled"))
        totals = (extras or {}).get("disables")
        if totals is None:
            xl.addWidget(small("Not recorded for this game."))
        elif not totals:
            xl.addWidget(small("None - nobody stunned, hexed or silenced you "
                               "(or it was too short to see).", TEXT, 13))
        else:
            chips = QHBoxLayout()
            for c in ui.CONTROL_COLORS:
                if c in totals:
                    chips.addWidget(small(
                        f"<span style='color:{ui.CONTROL_COLORS[c]}'>■</span>"
                        f" {c.capitalize()} <b>{totals[c]:.1f}s</b>", TEXT, 13))
            chips.addStretch()
            xl.addLayout(chips)
        xl.addWidget(small("Seen live from your hero. Neither Dota nor OpenDota "
                           "says who disabled you.", SUBTLE, 11))
        lay.addWidget(dis)
        lay.addStretch()
        self.scroll.setWidget(body)

    def _hero_row(self, x, scale):
        ctl = self.ctl
        name = ctl.hero_name(x["hero"])
        r = QHBoxLayout()
        r.setSpacing(12)
        r.addWidget(Portrait(ctl.portrait(x["hero"]), name, QSize(48, 27)))
        col = QVBoxLayout()
        col.setSpacing(3)
        top = QHBoxLayout()
        top.addWidget(small(name, TEXT, 13))
        top.addStretch()
        top.addWidget(small(f"<b>{x['total']:,}</b>", TEXT, 13))
        col.addLayout(top)
        col.addWidget(SplitBar(x["spells"], x["attacks"], scale))
        r.addLayout(col, 1)
        return r

    def _spell_row(self, s):
        r = QHBoxLayout()
        r.setSpacing(8)
        r.addWidget(small(f"<span style='color:{TYPE_COLORS[s['type']]}'>●"
                          f"</span>", TEXT, 13))
        who = self.ctl.hero_name(s["hero"]) if s["hero"] else "item"
        r.addWidget(small(f"{s['name']}  <span style='color:{SUBTLE}'>"
                          f"{who} · {s['type'].lower()}</span>", TEXT, 13), 1)
        r.addWidget(small(f"{s['amount']:,}", TEXT, 13))
        return r

    @staticmethod
    def _deaths(report, extras):
        """Pair OpenDota's deaths (time, killer) with the live recaps by
        game time. Either side may be missing."""
        recaps = list((extras or {}).get("deaths") or [])
        out = []
        for dth in (report or {}).get("deaths") or []:
            match = None
            for rc in recaps:
                if abs((rc.get("clock") or 0) - (dth["time"] or 0)) <= 6:
                    match = rc
                    break
            if match:
                recaps.remove(match)
            out.append((dth["time"], dth["killer"], match))
        for rc in recaps:                   # recorded live, not in report
            out.append((rc.get("clock"), None, rc))
        out.sort(key=lambda x: x[0] or 0)
        return out
