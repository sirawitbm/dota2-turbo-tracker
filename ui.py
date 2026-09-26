"""Turbo Tracker widgets (PySide6): theme, main window, recap card, panel.

No game logic here - turbo_tracker.py feeds these widgets plain dicts.
"""

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRect,
                            QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics,
                           QGuiApplication,
                           QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap, QStandardItem,
                           QStandardItemModel)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                               QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QListView, QMenu, QPushButton,
                               QSizePolicy, QStackedWidget, QStyle,
                               QStyledItemDelegate, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

import winutil

# ---------------------------------------------------------------------------
# theme
# ---------------------------------------------------------------------------

BG = "#0e1014"
SURFACE = "#161920"
SURFACE_2 = "#1d2129"
HOVER = "#232834"
BORDER = "#262b36"
TEXT = "#eef1f6"
MUTED = "#8b93a5"
SUBTLE = "#5d6576"
WIN = "#34d399"
LOSS = "#f87171"
ACCENT = "#ff9f43"
ACCENT_2 = "#ff6b3d"

FAMILY = "Segoe UI Variable Text"
DISPLAY = "Segoe UI Variable Display"

QSS = f"""
* {{ font-family: "{FAMILY}", "Segoe UI"; color: {TEXT}; }}
QWidget#main {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER};
              border-radius: 16px; }}
QLabel#caption {{ color: {MUTED}; font-size: 11px; font-weight: 600;
                 letter-spacing: 0.6px; }}
QLabel#value {{ font-family: "{DISPLAY}", "Segoe UI"; font-size: 28px;
               font-weight: 600; }}
QLabel#sub {{ color: {MUTED}; font-size: 12px; }}
QLabel#title {{ font-family: "{DISPLAY}", "Segoe UI"; font-size: 22px;
               font-weight: 700; }}
QLabel#tagline {{ color: {MUTED}; font-size: 12px; }}
QFrame#pill {{ background: {SURFACE}; border: 1px solid {BORDER};
              border-radius: 16px; }}
QFrame#banner {{ background: rgba(255,159,67,0.09);
                border: 1px solid rgba(255,159,67,0.35);
                border-radius: 12px; }}
QLabel#bannerText {{ color: #ffd6a8; font-size: 13px; }}
QFrame#update {{ background: rgba(52,211,153,0.08);
                border: 1px solid rgba(52,211,153,0.35);
                border-radius: 12px; }}
QLabel#updateText {{ color: #b9f3dc; font-size: 13px; }}
QFrame#seg {{ background: {SURFACE}; border: 1px solid {BORDER};
             border-radius: 12px; }}
QPushButton#segbtn {{ background: transparent; color: {MUTED}; border: none;
                     border-radius: 9px; padding: 7px 16px; font-size: 13px;
                     font-weight: 600; }}
QPushButton#segbtn:hover {{ color: {TEXT}; }}
QPushButton#segbtn:checked {{ background: {HOVER}; color: {TEXT}; }}
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {ACCENT}, stop:1 {ACCENT_2});
    color: #1b0f04; border: none; border-radius: 10px;
    padding: 8px 18px; font-size: 13px; font-weight: 700; }}
QPushButton#primary:hover {{ background: {ACCENT}; }}
QPushButton#ghost {{ background: {SURFACE}; border: 1px solid {BORDER};
                    border-radius: 10px; padding: 8px 18px; font-size: 13px;
                    font-weight: 600; }}
QPushButton#ghost:hover {{ background: {HOVER}; }}
QListView {{ background: transparent; border: none; outline: 0; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px;
                              min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {SUBTLE}; }}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}
QMenu {{ background: {SURFACE_2}; border: 1px solid {BORDER};
        border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 8px 18px; border-radius: 8px; font-size: 13px; }}
QMenu::item:selected {{ background: {HOVER}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
"""


def apply_theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, color in [(QPalette.Window, BG), (QPalette.Base, SURFACE),
                        (QPalette.Text, TEXT), (QPalette.WindowText, TEXT),
                        (QPalette.Button, SURFACE), (QPalette.ButtonText, TEXT),
                        (QPalette.Highlight, HOVER),
                        (QPalette.HighlightedText, TEXT)]:
        pal.setColor(role, QColor(color))
    app.setPalette(pal)
    app.setFont(QFont(FAMILY, 10))
    app.setStyleSheet(QSS)
    app.setWindowIcon(app_icon())


def font(size, weight=QFont.Normal, display=False):
    f = QFont(DISPLAY if display else FAMILY)
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def tint(color, alpha):
    c = QColor(color)
    c.setAlpha(alpha)
    return c


def app_icon():
    """A rounded orange square with a lightning bolt, drawn in code."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 64, 64)
    grad.setColorAt(0, QColor(ACCENT))
    grad.setColorAt(1, QColor(ACCENT_2))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    bolt = QPainterPath()
    for i, (x, y) in enumerate([(36, 10), (18, 36), (30, 36), (26, 54),
                                (46, 26), (34, 26), (38, 10)]):
        bolt.moveTo(x, y) if i == 0 else bolt.lineTo(x, y)
    bolt.closeSubpath()
    p.setBrush(QColor("#1b0f04"))
    p.drawPath(bolt)
    p.end()
    return QIcon(pix)


def draw_portrait(p, rect, pix, label, radius=8):
    """Hero picture with rounded corners, or initials while it downloads."""
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    p.save()
    p.setClipPath(path)
    if pix and not pix.isNull():
        scaled = pix.scaled(rect.size(), Qt.KeepAspectRatioByExpanding,
                            Qt.SmoothTransformation)
        sx = (scaled.width() - rect.width()) // 2
        sy = (scaled.height() - rect.height()) // 2
        p.drawPixmap(rect, scaled, QRect(sx, sy, rect.width(), rect.height()))
    else:
        p.fillRect(rect, QColor(SURFACE_2))
        p.setPen(QColor(SUBTLE))
        p.setFont(font(13, QFont.Bold))
        initials = "".join(w[0] for w in label.split()[:2]).upper() or "?"
        p.drawText(rect, Qt.AlignCenter, initials)
    p.restore()


def draw_pill(p, rect, text, color, size=11, backing=False):
    p.save()
    p.setPen(Qt.NoPen)
    if backing:      # dark base so the pill reads over a busy picture
        p.setBrush(tint("#0b0d11", 200))
        p.drawRoundedRect(QRectF(rect), rect.height() / 2, rect.height() / 2)
    p.setBrush(tint(color, 38))
    p.drawRoundedRect(QRectF(rect), rect.height() / 2, rect.height() / 2)
    p.setPen(QColor(color))
    p.setFont(font(size, QFont.Bold))
    p.drawText(rect, Qt.AlignCenter, text)
    p.restore()


# ---------------------------------------------------------------------------
# small building blocks
# ---------------------------------------------------------------------------

def setup_gsi_flag():
    import setup_gsi
    return setup_gsi.FLAG


def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def label(text="", name=None):
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    return lbl


def button(text, name="ghost", on_click=None):
    b = QPushButton(text)
    b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    return b


class Segmented(QFrame):
    """Pill-shaped switch between a few choices."""
    changed = Signal(str)

    def __init__(self, choices, value):
        super().__init__()
        self.setObjectName("seg")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for text, key in choices:
            b = button(text, "segbtn")
            b.setCheckable(True)
            b.setChecked(key == value)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            row.addWidget(b)
            self.buttons[key] = b

    def set_value(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class RatioBar(QWidget):
    """Thin rounded bar: green share = wins, red = losses."""

    def __init__(self):
        super().__init__()
        self.wins = self.losses = 0
        self.setFixedHeight(6)

    def set(self, wins, losses):
        self.wins, self.losses = wins, losses
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(r, 3, 3)
        total = self.wins + self.losses
        if total:
            w = r.width() * self.wins / total
            path = QPainterPath()
            path.addRoundedRect(r, 3, 3)
            p.setClipPath(path)
            p.fillRect(QRectF(r.left(), r.top(), w, r.height()), QColor(WIN))
            p.fillRect(QRectF(r.left() + w + 2, r.top(),
                              r.width() - w - 2, r.height()), QColor(LOSS))


class StatTile(QFrame):
    def __init__(self, caption, bar=False):
        super().__init__()
        self.setObjectName("card")
        box = QVBoxLayout(self)
        box.setContentsMargins(20, 16, 20, 16)
        box.setSpacing(4)
        box.addWidget(label(caption.upper(), "caption"))
        self.value = label("-", "value")
        box.addWidget(self.value)
        self.bar = RatioBar() if bar else None
        if self.bar:
            box.addSpacing(4)
            box.addWidget(self.bar)
        self.sub = label("", "sub")
        box.addWidget(self.sub)

    def set(self, value, sub="", color=TEXT):
        self.value.setText(value)
        self.value.setStyleSheet(f"color: {color};")
        self.sub.setText(sub)


class StatusPill(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("pill")
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 7, 16, 7)
        row.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        self.text = label("")
        self.text.setStyleSheet("font-size: 13px;")
        row.addWidget(self.dot)
        row.addWidget(self.text)
        self.set(SUBTLE, "Waiting for Dota")

    def set(self, color, text):
        self.dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
        self.text.setText(text)
        self.text.setStyleSheet(
            f"font-size: 13px; color: {TEXT if color == WIN else MUTED};")


# ---------------------------------------------------------------------------
# match and hero lists (painted rows)
# ---------------------------------------------------------------------------

ROW_H = 64
MATCH_COLS = [("result", "RESULT", 90), ("kda", "K / D / A", 110),
              ("length", "LENGTH", 80), ("gpm", "GPM", 70), ("xpm", "XPM", 70),
              ("lh", "LH / DN", 90)]
HERO_COLS = [("games", "GAMES", 70), ("record", "W - L", 80),
             ("rate", "WIN RATE", 150), ("kda", "AVG K / D / A", 130),
             ("gpm", "AVG GPM", 90)]
PORTRAIT = QSize(68, 38)


def column_rects(rect, cols):
    """Fixed-width columns packed against the right edge of a row."""
    x = rect.right() - 18 - sum(w for _, _, w in cols)
    out = {}
    for key, _, w in cols:
        out[key] = QRect(x, rect.top(), w, rect.height())
        x += w
    return out, x - sum(w for _, _, w in cols)


class ListHeader(QWidget):
    def __init__(self, cols, first="HERO"):
        super().__init__()
        self.cols, self.first = cols, first
        self.setFixedHeight(30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setPen(QColor(SUBTLE))
        p.setFont(font(11, QFont.DemiBold))
        r = self.rect()
        rects, start = column_rects(r, self.cols)
        p.drawText(QRect(14 + PORTRAIT.width() + 14, 0, 200, r.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.first)
        for key, title, _ in self.cols:
            p.drawText(rects[key], Qt.AlignCenter, title)


class RowDelegate(QStyledItemDelegate):
    def __init__(self, cols, portrait_for, parent=None):
        super().__init__(parent)
        self.cols = cols
        self.portrait_for = portrait_for

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), ROW_H)

    def paint(self, p, option, index):
        row = index.data(Qt.UserRole)
        if not row:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = option.rect.adjusted(4, 3, -4, -3)
        if option.state & QStyle.State_MouseOver:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(HOVER))
            p.drawRoundedRect(QRectF(r), 12, 12)

        pr = QRect(QPoint(r.left() + 10, r.center().y() - PORTRAIT.height() // 2),
                   PORTRAIT)
        draw_portrait(p, pr, self.portrait_for(row["hero_internal"]),
                      row["hero"])
        rects, start = column_rects(r, self.cols)
        tx = pr.right() + 14
        p.setPen(QColor(TEXT))
        p.setFont(font(14, QFont.DemiBold))
        name_r = QRect(tx, r.top() + 12, start - tx - 8, 20)
        p.drawText(name_r, Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(p.font()).elidedText(row["hero"], Qt.ElideRight,
                                                     name_r.width()))
        p.setPen(QColor(MUTED))
        p.setFont(font(12))
        p.drawText(QRect(tx, r.top() + 33, start - tx - 8, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, row["subtitle"])
        self.paint_cells(p, rects, row)
        p.restore()

    def paint_cells(self, p, rects, row):
        raise NotImplementedError


class MatchDelegate(RowDelegate):
    def __init__(self, portrait_for, parent=None):
        super().__init__(MATCH_COLS, portrait_for, parent)

    def paint_cells(self, p, rects, row):
        rr = rects["result"]
        color = {1: WIN, 0: LOSS}.get(row["won"], SUBTLE)
        text = {1: "WIN", 0: "LOSS"}.get(row["won"], "?")
        draw_pill(p, QRect(rr.center().x() - 28, rr.center().y() - 12, 56, 24),
                  text, color)
        p.setFont(font(14, QFont.DemiBold))
        p.setPen(QColor(TEXT))
        p.drawText(rects["kda"], Qt.AlignCenter, row["kda"])
        p.setFont(font(13))
        for key in ("length", "gpm", "xpm", "lh"):
            p.setPen(QColor(TEXT if key != "lh" else MUTED))
            p.drawText(rects[key], Qt.AlignCenter, str(row[key]))


class HeroDelegate(RowDelegate):
    def __init__(self, portrait_for, parent=None):
        super().__init__(HERO_COLS, portrait_for, parent)

    def paint_cells(self, p, rects, row):
        p.setFont(font(14, QFont.DemiBold))
        p.setPen(QColor(TEXT))
        p.drawText(rects["games"], Qt.AlignCenter, str(row["games"]))
        p.setFont(font(13))
        p.drawText(rects["record"], Qt.AlignCenter, row["record"])
        p.drawText(rects["kda"], Qt.AlignCenter, row["kda"])
        p.drawText(rects["gpm"], Qt.AlignCenter, str(row["gpm"]))

        rr = rects["rate"]
        rate = row["rate"]
        color = SUBTLE if rate is None else (WIN if rate >= 50 else LOSS)
        p.setPen(QColor(TEXT))
        p.setFont(font(13, QFont.DemiBold))
        p.drawText(QRect(rr.left() + 8, rr.top(), 44, rr.height()),
                   Qt.AlignVCenter | Qt.AlignRight,
                   "-" if rate is None else f"{rate}%")
        bar = QRectF(rr.left() + 62, rr.center().y() - 3, 76, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(bar, 3, 3)
        if rate:
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(),
                                     max(6, bar.width() * rate / 100), 6), 3, 3)


class RowList(QWidget):
    """Header + painted list + empty-state message, inside a card."""

    def __init__(self, cols, delegate):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        box.addWidget(ListHeader(cols))
        self.stack = QStackedWidget()
        self.model = QStandardItemModel(self)
        self.view = QListView()
        self.view.setModel(self.model)
        self.view.setItemDelegate(delegate)
        delegate.setParent(self.view)
        self.view.setMouseTracking(True)
        self.view.viewport().setAttribute(Qt.WA_Hover)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setUniformItemSizes(True)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.empty = label("", "sub")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.setStyleSheet(f"color: {MUTED}; font-size: 14px;")
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.empty)
        box.addWidget(self.stack)

    def set_rows(self, rows, empty_text):
        self.model.clear()
        for row in rows:
            item = QStandardItem()
            item.setData(row, Qt.UserRole)
            item.setEditable(False)
            self.model.appendRow(item)
        self.empty.setText(empty_text)
        self.stack.setCurrentIndex(0 if rows else 1)

    def repaint_rows(self):
        self.view.viewport().update()


# ---------------------------------------------------------------------------
# main window
# ---------------------------------------------------------------------------

class MainWindow(QWidget):
    closed = Signal()

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.setObjectName("main")
        self.setWindowTitle("Turbo Tracker")
        self.resize(1120, 720)
        self.setMinimumSize(1060, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(16)

        # header
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(40, 40))
        head.addWidget(logo)
        head.addSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label("Turbo Tracker", "title"))
        titles.addWidget(label("Your Dota 2 Turbo games, logged live"
                               f"  ·  v{ctl.version}", "tagline"))
        head.addLayout(titles)
        head.addStretch()
        self.status = StatusPill()
        head.addWidget(self.status, 0, Qt.AlignVCenter)
        root.addLayout(head)

        # setup banner
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        brow = QHBoxLayout(self.banner)
        brow.setContentsMargins(16, 12, 12, 12)
        self.banner_text = label("", "bannerText")
        self.banner_text.setWordWrap(True)
        brow.addWidget(self.banner_text, 1)
        self.banner_copy = button(f"Copy  {setup_gsi_flag()}", "ghost",
                                  self._copy_flag)
        brow.addWidget(self.banner_copy)
        self.banner_btn = button("Set up now", "primary", ctl.run_setup)
        brow.addWidget(self.banner_btn)
        self.banner.hide()
        root.addWidget(self.banner)

        # update available (hidden until a newer release is found)
        self.update_bar = QFrame()
        self.update_bar.setObjectName("update")
        urow = QHBoxLayout(self.update_bar)
        urow.setContentsMargins(16, 10, 12, 10)
        urow.setSpacing(8)
        self.update_text = label("", "updateText")
        urow.addWidget(self.update_text, 1)
        urow.addWidget(button("Later", "ghost", ctl.skip_update))
        urow.addWidget(button("Download", "primary", ctl.open_update))
        self.update_bar.hide()
        root.addWidget(self.update_bar)

        # stat tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(14)
        self.t_games = StatTile("Games")
        self.t_record = StatTile("Win - Loss", bar=True)
        self.t_rate = StatTile("Win rate")
        self.t_streak = StatTile("Streak")
        for t in (self.t_games, self.t_record, self.t_rate, self.t_streak):
            tiles.addWidget(t, 1)
        root.addLayout(tiles)

        # toolbar
        bar = QHBoxLayout()
        self.tabs = Segmented([("Matches", "matches"), ("Heroes", "heroes")],
                              "matches")
        self.tabs.changed.connect(self._switch_tab)
        bar.addWidget(self.tabs)
        bar.addStretch()
        self.filter = Segmented([("All games", "all"), ("Turbo only", "turbo")],
                                "turbo" if ctl.settings["turbo_only"] else "all")
        self.filter.changed.connect(ctl.set_filter)
        bar.addWidget(self.filter)
        bar.addSpacing(10)
        bar.addWidget(button("Show last recap", "ghost", ctl.show_last_recap))
        root.addLayout(bar)

        # lists
        body = card()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(8, 8, 8, 8)
        self.pages = QStackedWidget()
        self.matches = RowList(MATCH_COLS, MatchDelegate(ctl.portrait))
        self.heroes = RowList(HERO_COLS, HeroDelegate(ctl.portrait))
        self.pages.addWidget(self.matches)
        self.pages.addWidget(self.heroes)
        blay.addWidget(self.pages)
        root.addWidget(body, 1)

        # footer
        foot = QHBoxLayout()
        foot.addWidget(label("RECAP STYLE", "caption"))
        foot.addSpacing(6)
        self.recap = Segmented([("Popup", "popup"),
                                ("Taskbar panel", "panel")],
                               ctl.settings["recap_mode"])
        self.recap.changed.connect(ctl.set_recap_mode)
        foot.addWidget(self.recap)
        foot.addSpacing(22)
        foot.addWidget(label("IN-GAME TIPS", "caption"))
        foot.addSpacing(6)
        choices = [("Off", "off"), ("Game screen", "game")]
        if len(QGuiApplication.screens()) > 1:
            choices.append(("2nd screen", "second"))
        self.tips = Segmented(choices, ctl.settings["tips"])
        self.tips.changed.connect(ctl.set_tips)
        foot.addWidget(self.tips)
        foot.addSpacing(8)
        self.tips_size = Segmented([("Full", "full"), ("Small", "small")],
                                   ctl.settings["tips_size"])
        self.tips_size.changed.connect(ctl.set_tips_size)
        foot.addWidget(self.tips_size)
        foot.addStretch()
        root.addLayout(foot)

    def _switch_tab(self, key):
        self.pages.setCurrentIndex(0 if key == "matches" else 1)

    def set_banner(self, text, show_button, show_copy=False):
        if not text:
            self.banner.hide()
            return
        self.banner_text.setText(text)
        self.banner_btn.setVisible(show_button)
        self.banner_copy.setVisible(show_copy)
        self.banner.show()

    def _copy_flag(self):
        QGuiApplication.clipboard().setText(setup_gsi_flag())
        self.banner_copy.setText("Copied \u2713  now paste it in Steam")
        QTimer.singleShot(3000, lambda: self.banner_copy.setText(
            f"Copy  {setup_gsi_flag()}"))

    def set_update(self, version, current):
        if not version:
            self.update_bar.hide()
            return
        self.update_text.setText(
            f"Turbo Tracker {version} is out  ·  you have {current}")
        self.update_bar.show()

    def showEvent(self, event):
        super().showEvent(event)
        winutil.dark_title_bar(int(self.winId()))

    def closeEvent(self, event):
        # The close button is routed to the controller (hide in panel mode,
        # quit otherwise). But when the app itself is quitting this must say
        # yes: Qt 6 cancels a quit if any window refuses to close.
        if getattr(self.ctl, "quitting", False):
            event.accept()
            return
        event.ignore()
        self.closed.emit()


# ---------------------------------------------------------------------------
# floating windows shared bits
# ---------------------------------------------------------------------------

def rounded_menu():
    """A QMenu whose rounded QSS corners aren't boxed in by a square frame."""
    menu = QMenu()
    menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint
                        | Qt.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WA_TranslucentBackground)
    return menu


class Tray(QSystemTrayIcon):
    """Icon in the notification area: click to open, right-click for more.

    Qt re-adds the icon itself when Explorer restarts (the TaskbarCreated
    case from the skill), so there's no Win32 code here.
    """

    def __init__(self, on_open, on_recap, on_quit):
        super().__init__(app_icon())
        self.setToolTip("Turbo Tracker")
        self.menu = rounded_menu()
        self.menu.addAction("Open Turbo Tracker", on_open)
        self.menu.addAction("Show last recap", on_recap)
        self._on_update = None
        self.update_action = self.menu.addAction(
            "Update available", lambda: self._on_update and self._on_update())
        self.update_action.setVisible(False)
        self.menu.addSeparator()
        self.menu.addAction("Quit", on_quit)
        self.setContextMenu(self.menu)
        self.activated.connect(
            lambda reason: on_open() if reason in (
                QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)

    def set_update(self, version, on_click):
        self._on_update = on_click if version else None
        self.update_action.setVisible(bool(version))
        if version:
            self.update_action.setText(f"Download update {version}")


FLOAT_FLAGS = (Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
               | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)


def primary_areas():
    """(full screen rect, work area rect) of the primary screen, in Qt's
    logical pixels."""
    screen = QGuiApplication.primaryScreen()
    return screen.geometry(), screen.availableGeometry(), screen.devicePixelRatio()


# ---------------------------------------------------------------------------
# recap card
# ---------------------------------------------------------------------------

class HeroBanner(QWidget):
    """Hero portrait with a fade to the card colour and the result on top."""

    def __init__(self, info, pix):
        super().__init__()
        self.info, self.pix = info, pix
        self.setFixedHeight(150)

    def set_pixmap(self, pix):
        self.pix = pix
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.rect()
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(r).adjusted(0, 0, 0, 20), 18, 18)
        p.setClipPath(clip)
        if self.pix and not self.pix.isNull():
            scaled = self.pix.scaled(r.size(), Qt.KeepAspectRatioByExpanding,
                                     Qt.SmoothTransformation)
            sy = max(0, (scaled.height() - r.height()) // 3)
            p.drawPixmap(r, scaled, QRect((scaled.width() - r.width()) // 2,
                                          sy, r.width(), r.height()))
        else:
            g = QLinearGradient(0, 0, r.width(), r.height())
            g.setColorAt(0, tint(self.info["color"], 70))
            g.setColorAt(1, QColor(SURFACE_2))
            p.fillRect(r, g)
        fade = QLinearGradient(0, 0, 0, r.height())
        fade.setColorAt(0, tint(SURFACE, 40))
        fade.setColorAt(0.55, tint(SURFACE, 120))
        fade.setColorAt(1, QColor(SURFACE))
        p.fillRect(r, fade)

        draw_pill(p, QRect(18, 16, 96, 26), self.info["result"],
                  self.info["color"], 12, backing=True)
        chip = QRect(r.width() - 18 - 64, 16, 64, 26)
        p.setPen(Qt.NoPen)
        p.setBrush(tint("#0b0d11", 200))
        p.drawRoundedRect(QRectF(chip), 13, 13)
        p.setPen(QColor(TEXT))
        p.setFont(font(12, QFont.DemiBold))
        p.drawText(chip, Qt.AlignCenter, self.info["length"])

        p.setFont(font(26, QFont.Bold, display=True))
        p.setPen(QColor(TEXT))
        p.drawText(QRect(20, r.height() - 48, r.width() - 40, 40),
                   Qt.AlignLeft | Qt.AlignVCenter, self.info["hero"])


class Countdown(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(4)
        self.fraction = 1.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SURFACE_2))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 4), 2, 2)
        if self.fraction <= 0:
            return
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(ACCENT))
        g.setColorAt(1, QColor(ACCENT_2))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(0, 0, max(4, self.width() * self.fraction), 4),
                          2, 2)


class RecapCard(QWidget):
    WIDTH = 380
    SHADOW = 24

    def __init__(self, info, pix, on_close, anchor=None, timeout=20):
        super().__init__(None, FLOAT_FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.on_close = on_close
        self.timeout = timeout
        self.remaining = float(timeout or 0)
        self.hovered = False

        outer = QVBoxLayout(self)
        m = self.SHADOW
        outer.setContentsMargins(m, m, m, m)
        self.body = QFrame()
        self.body.setObjectName("recap")
        self.body.setStyleSheet(
            f"QFrame#recap {{ background: {SURFACE}; border: 1px solid {BORDER};"
            f" border-radius: 18px; }}")
        shadow = QGraphicsDropShadowEffect(self.body)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 170))
        self.body.setGraphicsEffect(shadow)
        outer.addWidget(self.body)

        box = QVBoxLayout(self.body)
        box.setContentsMargins(1, 1, 1, 0)
        box.setSpacing(0)
        self.banner = HeroBanner(info, pix)
        box.addWidget(self.banner)

        content = QVBoxLayout()
        content.setContentsMargins(20, 6, 20, 16)
        content.setSpacing(12)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        for value, cap in zip(info["kda_parts"], ("KILLS", "DEATHS", "ASSISTS")):
            stats.addWidget(self._stat(str(value), cap), 1)
        content.addLayout(stats)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        for text in info["chips"]:
            chip = label(text)
            chip.setStyleSheet(
                f"background: {SURFACE_2}; border: 1px solid {BORDER};"
                f" border-radius: 10px; padding: 4px 10px; color: {MUTED};"
                " font-size: 12px;")
            chips.addWidget(chip)
        chips.addStretch()
        content.addLayout(chips)

        fact = label(info["fact"])
        fact.setWordWrap(True)
        fact.setStyleSheet("font-size: 13px;")
        content.addWidget(fact)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {BORDER};")
        content.addWidget(line)

        foot = QHBoxLayout()
        today = label(info["today"])
        today.setStyleSheet(f"color: {ACCENT}; font-size: 13px;"
                            " font-weight: 700;")
        foot.addWidget(today)
        foot.addStretch()
        self.mode = label(info["mode"])
        self.mode.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        foot.addWidget(self.mode)
        content.addLayout(foot)
        self.countdown = Countdown()
        content.addWidget(self.countdown)
        box.addLayout(content)
        if not timeout:
            self.countdown.hide()

        self.setFixedWidth(self.WIDTH + 2 * m)
        self.adjustSize()
        self._place(anchor)

        self.setWindowOpacity(0.0)
        self.show()
        winutil.pin_topmost(int(self.winId()))
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(260)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(320)
        self._slide.setStartValue(self.pos() + QPoint(0, 16))
        self._slide.setEndValue(self.pos())
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.start()
        self._slide.start()

        if timeout:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(50)

    def _stat(self, value, caption):
        f = QFrame()
        f.setStyleSheet(f"background: {SURFACE_2}; border-radius: 12px;")
        v = QVBoxLayout(f)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(0)
        num = label(value)
        num.setStyleSheet(f"font-family: '{DISPLAY}'; font-size: 24px;"
                          " font-weight: 700;")
        cap = label(caption)
        cap.setStyleSheet(f"color: {MUTED}; font-size: 10px;"
                          " font-weight: 700; letter-spacing: 0.6px;")
        v.addWidget(num, 0, Qt.AlignHCenter)
        v.addWidget(cap, 0, Qt.AlignHCenter)
        return f

    def _place(self, anchor):
        full, work, _ = primary_areas()
        m = self.SHADOW
        if anchor is not None and anchor.isVisible():
            # Beside the panel, wherever it has been dragged: above it,
            # or below if it sits near the top of the screen.
            a = anchor.geometry()
            x = a.center().x() - self.width() // 2
            y = a.top() - self.height() + m - 8
            if y < full.top():
                y = a.bottom() - m + 8
            x = max(full.left() - m, min(x, full.right() - self.width() + m))
            self.move(x, y)
            return
        x = work.right() - self.width() + m - 12
        y = work.bottom() - self.height() + m - 12
        self.move(max(work.left(), x), y)

    def _tick(self):
        if self.hovered:
            return
        self.remaining -= 0.05
        self.countdown.fraction = max(0.0, self.remaining / self.timeout)
        self.countdown.update()
        if self.remaining <= 0:
            self.dismiss()

    def set_mode(self, text):
        self.mode.setText(text)

    def set_pixmap(self, pix):
        self.banner.set_pixmap(pix)

    def enterEvent(self, _):
        self.hovered = True

    def leaveEvent(self, _):
        self.hovered = False

    def mousePressEvent(self, _):
        self.dismiss()

    def dismiss(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        if hasattr(self, "_timer"):
            self._timer.stop()
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(180)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.finished.connect(self.close)
        fade.start()
        self._fade_out = fade
        self.on_close(self)


# ---------------------------------------------------------------------------
# tips card (while dead or paused)
# ---------------------------------------------------------------------------

class ItemTile(QWidget):
    """Item icon with rounded corners, a tick if you own it, name below."""

    def __init__(self, item, pix, size):
        super().__init__()
        self.item, self.pix, self.icon = item, pix, size
        self.setFixedSize(max(size.width() + 16, 92), size.height() + 22)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRect((self.width() - self.icon.width()) // 2, 0,
                  self.icon.width(), self.icon.height())
        owned = self.item.get("owned")
        if owned:
            p.setOpacity(0.55)
        draw_portrait(p, r, self.pix, self.item["name"], radius=6)
        p.setOpacity(1.0)
        if owned:
            badge = QRectF(r.right() - 13, r.top() - 3, 16, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(WIN))
            p.drawEllipse(badge)
            p.setPen(QPen(QColor("#0b0d11"), 2))
            c = badge.center()
            p.drawPolyline([QPoint(int(c.x() - 4), int(c.y())),
                            QPoint(int(c.x() - 1), int(c.y() + 3)),
                            QPoint(int(c.x() + 4), int(c.y() - 3))])
        p.setPen(QColor(MUTED if owned else TEXT))
        p.setFont(font(10, QFont.DemiBold))
        name_r = QRect(0, r.bottom() + 4, self.width(), 16)
        p.drawText(name_r, Qt.AlignHCenter | Qt.AlignTop,
                   QFontMetrics(p.font()).elidedText(self.item["name"],
                                                     Qt.ElideRight,
                                                     self.width()))


class TipsCard(QWidget):
    """Shown only while you're dead or the game is paused, like Dota's own
    pause tips. Click-through and never takes focus, so it can't get in the
    way of the game; the controller hides it the instant you're back."""

    WIDTH = 560
    BIG = QSize(64, 47)      # Dota item art is 88x64
    SMALL = QSize(48, 35)

    def __init__(self, icon_for):
        super().__init__(None, FLOAT_FLAGS | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.icon_for = icon_for
        self._sig = None
        self.compact = False
        self.on_hotkey = None
        self.hotkey_on = False
        self.setFixedWidth(self.WIDTH)

        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(22, 16, 22, 18)
        self.box.setSpacing(8)
        head = QHBoxLayout()
        self.headline = label("")
        self.headline.setStyleSheet("font-size: 15px; font-weight: 700;")
        head.addWidget(self.headline)
        # Small size: the item names go on this same line instead.
        self.line = label("")
        self.line.setStyleSheet(f"font-size: 13px; color: {TEXT};")
        self.line.hide()
        head.addSpacing(10)
        head.addWidget(self.line)
        head.addStretch()
        self.context = label("")
        self.context.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        head.addWidget(self.context)
        self.box.addLayout(head)
        self.body = QWidget()
        self.box.addWidget(self.body)
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(tint(BG, 235))
        radius = r.height() / 2 if self.compact else 16
        p.drawRoundedRect(r, radius, radius)

    def set_compact(self, compact):
        """Full card with item pictures, or one slim line of text."""
        if compact == self.compact:
            return
        self.compact = compact
        self._sig = None                    # force a rebuild
        self.line.setVisible(compact)
        self.context.setVisible(not compact)
        if compact:
            self.box.setContentsMargins(18, 8, 20, 8)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        else:
            self.box.setContentsMargins(22, 16, 22, 18)
            self.setFixedWidth(self.WIDTH)
        self.update()

    def _fit(self):
        # setText only *posts* a relayout; without activating it first,
        # adjustSize measures the old text and the new one gets clipped.
        self.box.invalidate()
        self.box.activate()
        self.adjustSize()

    @staticmethod
    def compact_text(rec, message):
        """The popular items you don't have yet, in one line."""
        if message or not rec:
            return message or "No item data yet"
        todo = [it["name"] for it in rec["now"] if not it["owned"]][:3]
        if todo:
            return "Next: " + "  ·  ".join(todo)
        later = [it["name"] for it in rec["next"]][:3]
        if later:
            return "Later: " + "  ·  ".join(later)
        return "You have the popular items"

    def set_headline(self, text, color):
        self.headline.setText(text)
        self.headline.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {color};")

    def set_content(self, context, rec, message=None):
        """rec from builds.recommend(); rebuilt only when it changes."""
        self.context.setText(context)
        sig = (message, repr(rec) if rec else None, self.compact)
        if sig == self._sig:
            return
        self._sig = sig
        if self.compact:
            self.line.setText(self.compact_text(rec, message))
            self.body.hide()
            self._fit()
            return
        self.box.removeWidget(self.body)
        self.body.deleteLater()
        self.body = QWidget()
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(6)
        if message or not rec:
            note = label(message or "No item data yet")
            note.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
            lay.addWidget(note)
        else:
            lay.addWidget(self._caption(f"POPULAR NOW · {rec['stage'].upper()}"))
            lay.addLayout(self._row(rec["now"], self.BIG))
            if rec["next"]:
                lay.addSpacing(4)
                lay.addWidget(self._caption(
                    f"COMING UP · {rec['next_stage'].upper()}"))
                lay.addLayout(self._row(rec["next"], self.SMALL))
            hint = label("Mouse over or Ctrl+Shift+T to shrink")
            hint.setStyleSheet(f"color: {SUBTLE}; font-size: 10px;")
            lay.addWidget(hint, 0, Qt.AlignRight)
        self.box.addWidget(self.body)
        self._fit()

    HOTKEY_ID = 0x7454          # any app-unique number
    HOTKEY_VK = 0x54            # T  (with Ctrl+Shift)

    def showEvent(self, event):
        super().showEvent(event)
        # Listen for Ctrl+Shift+T only while the card is up, so the combo
        # is free the rest of the time.
        self.hotkey_on = winutil.register_hotkey(
            int(self.winId()), self.HOTKEY_ID, self.HOTKEY_VK)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.hotkey_on:
            winutil.unregister_hotkey(int(self.winId()), self.HOTKEY_ID)
            self.hotkey_on = False

    def nativeEvent(self, event_type, message):
        if winutil.hotkey_id_of(message) == self.HOTKEY_ID and self.on_hotkey:
            self.on_hotkey()
            return True, 0
        return False, 0

    def pointer_over(self):
        return self.isVisible() and self.geometry().contains(QCursor.pos())

    def refresh_icons(self):
        for tile in self.body.findChildren(ItemTile):
            tile.pix = self.icon_for(tile.item)
            tile.update()

    def _caption(self, text):
        c = label(text)
        c.setStyleSheet(f"color: {SUBTLE}; font-size: 10px; font-weight: 700;"
                        " letter-spacing: 0.8px;")
        return c

    def _row(self, items, size):
        row = QHBoxLayout()
        row.setSpacing(2)
        for it in items:
            row.addWidget(ItemTile(it, self.icon_for(it), size))
        row.addStretch()
        return row

    def place(self, where):
        """"game": top middle of the main screen, under Dota's hero bar.
        "second": middle of another monitor (falls back to "game")."""
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        others = [s for s in screens if s is not primary]
        self._fit()
        if where == "second" and others:
            g = others[0].availableGeometry()
            self.move(g.center().x() - self.width() // 2,
                      g.center().y() - self.height() // 2)
            return
        g = primary.geometry()
        self.move(g.center().x() - self.width() // 2,
                  g.top() + int(g.height() * 0.10))


CONTROL_COLORS = {"stunned": "#f5b942", "hexed": "#6fcf6f",
                  "silenced": "#b48cf2", "disarmed": "#f28c8c",
                  "muted": "#7fb4f2", "break": "#9aa3b5"}


class HpGraph(QWidget):
    """Your HP over the seconds before death, with a lane per disable."""

    def __init__(self, recap):
        super().__init__()
        self.recap = recap
        lanes = len(recap["controls"])
        self.setFixedHeight(96 + lanes * 12)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.recap
        span = max(3.0, min(12.0, -r["hp"][0][0] if r["hp"] else 3.0))
        lanes = [c for c in CONTROL_COLORS if c in r["controls"]]
        w, h = self.width(), 80
        left, right = 34, w - 6

        def x(t):
            return left + (right - left) * (1 + t / span)

        # axes / grid
        p.setPen(QPen(QColor(BORDER), 1))
        for frac in (0, 0.5, 1):
            y = 6 + (h - 12) * (1 - frac)
            p.drawLine(QPoint(left, int(y)), QPoint(right, int(y)))
        p.setPen(QColor(SUBTLE))
        p.setFont(font(9))
        p.drawText(QRect(0, 0, left - 6, 14), Qt.AlignRight, "100%")
        p.drawText(QRect(0, h - 14, left - 6, 14), Qt.AlignRight, "0")
        for s in range(0, int(span) + 1, 2):
            y = h - 2 + len(lanes) * 12
            if s:
                p.drawText(QRect(int(x(-s)) - 20, y, 40, 14), Qt.AlignHCenter,
                           f"-{s}s")
            else:                        # keep "death" inside the card
                p.drawText(QRect(right - 44, y, 44, 14), Qt.AlignRight, "death")

        # HP area
        pts = [(x(t), 6 + (h - 12) * (1 - max(0.0, min(1.0, frac))))
               for t, frac in r["hp"] if t >= -span]
        if len(pts) >= 2:
            path = QPainterPath()
            path.moveTo(pts[0][0], h - 6)
            for px, py in pts:
                path.lineTo(px, py)
            path.lineTo(pts[-1][0], h - 6)
            path.closeSubpath()
            g = QLinearGradient(0, 0, 0, h)
            g.setColorAt(0, tint(LOSS, 120))
            g.setColorAt(1, tint(LOSS, 20))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawPath(path)
            line = QPainterPath()
            line.moveTo(*pts[0])
            for px, py in pts[1:]:
                line.lineTo(px, py)
            p.setPen(QPen(QColor(LOSS), 2))
            p.setBrush(Qt.NoBrush)
            p.drawPath(line)

        # disable lanes under the graph
        for i, c in enumerate(lanes):
            y = h + 2 + i * 12
            p.setPen(Qt.NoPen)
            p.setBrush(tint(BORDER, 160))
            p.drawRoundedRect(QRectF(left, y, right - left, 8), 4, 4)
            p.setBrush(QColor(CONTROL_COLORS[c]))
            for flag, t1, t2 in r["bands"]:
                if flag == c and t2 >= -span:
                    x1, x2 = x(max(t1, -span)), x(min(t2, 0))
                    p.drawRoundedRect(QRectF(x1, y, max(3, x2 - x1), 8), 4, 4)


class DeathRecapCard(QWidget):
    """Your latest death, on a hotkey (Ctrl+Shift+D) during a game.

    Built only from what Dota sends about your own hero: HP every 0.1 s and
    whether you're stunned / silenced / hexed etc. Dota's feed has no damage
    sources or types, so the card doesn't pretend to know them.
    Click-through and never takes focus, like the tips card.
    """

    WIDTH = 560
    HOTKEY_ID = 0x7444
    HOTKEY_VK = 0x44            # D  (with Ctrl+Shift)
    SECONDS = 12

    def __init__(self):
        super().__init__(None, FLOAT_FLAGS | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(self.WIDTH)
        self.on_hotkey = None
        self.hotkey_on = False
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(22, 16, 22, 16)
        self.box.setSpacing(8)
        self.body = QWidget()
        self.box.addWidget(self.body)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(tint(BG, 238))
        p.drawRoundedRect(r, 16, 16)

    # hotkey: only registered while a game is on (controller decides)
    def set_hotkey(self, on):
        if on == self.hotkey_on:
            return
        hwnd = int(self.winId())
        if on:
            self.hotkey_on = winutil.register_hotkey(hwnd, self.HOTKEY_ID,
                                                     self.HOTKEY_VK)
        else:
            winutil.unregister_hotkey(hwnd, self.HOTKEY_ID)
            self.hotkey_on = False

    def nativeEvent(self, event_type, message):
        if winutil.hotkey_id_of(message) == self.HOTKEY_ID and self.on_hotkey:
            self.on_hotkey()
            return True, 0
        return False, 0

    def show_recap(self, recap, number, fmt_clock, pos):
        self.box.removeWidget(self.body)
        self.body.deleteLater()
        self.body = QWidget()
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        head = QHBoxLayout()
        title = label("\u2620  NO DEATHS YET THIS GAME" if recap is None
                      else f"\u2620  DEATH {number}  \u00b7  {fmt_clock(recap['clock'])}")
        title.setStyleSheet(f"color: {LOSS if recap else WIN};"
                            " font-size: 15px; font-weight: 700;")
        head.addWidget(title)
        head.addStretch()
        if recap:
            speed = (f"from full HP \u2192 dead in {recap['window']:.1f}s"
                     if recap["from_pct"] >= 95 else
                     f"from {recap['from_pct']}% HP \u2192 dead in "
                     f"{recap['window']:.1f}s")
            sub = label(speed)
            sub.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            head.addWidget(sub)
        lay.addLayout(head)
        if recap:
            lay.addWidget(HpGraph(recap))
            bits = []
            for c in CONTROL_COLORS:
                if c in recap["controls"]:
                    bits.append(f"<span style='color:{CONTROL_COLORS[c]}'>"
                                f"\u25a0</span> {c.capitalize()} "
                                f"{recap['controls'][c]:.1f}s")
            if not bits:
                bits.append(f"<span style='color:{SUBTLE}'>No stuns, hexes or "
                            "silences before this death</span>")
            legend = QLabel("&nbsp;&nbsp;&nbsp;".join(bits))
            legend.setTextFormat(Qt.RichText)
            legend.setStyleSheet("font-size: 12px;")
            lay.addWidget(legend)
            per_s = recap["damage"] / recap["window"] if recap["window"] else 0
            totals = (f"Took {recap['damage']:,} damage in "
                      f"{recap['window']:.1f}s (\u2248{per_s:,.0f} per second)")
            if recap["heal"]:
                totals += f"  \u00b7  healed {recap['heal']:,}"
            t = label(totals)
            t.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
            lay.addWidget(t)
            note = label("From your HP and disables only - Dota doesn't share "
                         "which spell hit you.   Ctrl+Shift+D to hide")
            note.setStyleSheet(f"color: {SUBTLE}; font-size: 10px;")
            lay.addWidget(note)
        self.box.addWidget(self.body)
        self.box.invalidate()
        self.box.activate()
        self.adjustSize()
        self.move(pos(self))
        self.show()
        winutil.pin_topmost(int(self.winId()))
        self._timer.start((self.SECONDS if recap else 3) * 1000)


class ItemToast(QWidget):
    """A small note by Dota's kill feed after you finish an item, with the
    next three popular buys. Click-through, never takes focus, gone after
    a few seconds."""

    SECONDS = 7
    ICON = QSize(40, 29)

    def __init__(self, icon_for):
        super().__init__(None, FLOAT_FLAGS | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.icon_for = icon_for
        self.item = None
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 16, 6)
        row.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(self.ICON)
        row.addWidget(self.icon)
        text = QVBoxLayout()
        text.setSpacing(0)
        self.done = label("")
        self.done.setStyleSheet(f"color: {WIN}; font-size: 13px; font-weight: 700;")
        self.next = label("")
        self.next.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        text.addWidget(self.done)
        text.addWidget(self.next)
        row.addLayout(text)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._fade = None
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(tint(WIN, 90), 1))
        p.setBrush(tint(BG, 230))
        p.drawRoundedRect(r, 12, 12)

    def _set_icon(self):
        pix = self.icon_for(self.item) if self.item else None
        canvas = QPixmap(self.ICON * self.devicePixelRatioF())
        canvas.setDevicePixelRatio(self.devicePixelRatioF())
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        draw_portrait(p, QRect(QPoint(0, 0), self.ICON), pix,
                      self.item["name"] if self.item else "", radius=5)
        p.end()
        self.icon.setPixmap(canvas)

    def refresh_icons(self):
        if self.isVisible() and self.item:
            self._set_icon()

    def show_item(self, item, upcoming, where):
        self.item = item
        self.done.setText(f"✓  {item['name']} done")
        names = [it["name"] for it in upcoming]
        self.next.setText("Next: " + "  ·  ".join(names) if names
                          else "You have the popular items")
        self._set_icon()
        if self._fade:
            self._fade.stop()
        self.setWindowOpacity(1.0)
        self.layout().invalidate()
        self.layout().activate()
        self.adjustSize()
        self.place(where)
        self.show()
        winutil.pin_topmost(int(self.winId()))
        self._timer.start(self.SECONDS * 1000)

    def place(self, where):
        """Left edge, where Dota's kill feed is; on a second monitor, its
        top-left corner."""
        primary = QGuiApplication.primaryScreen()
        others = [s for s in QGuiApplication.screens() if s is not primary]
        if where == "second" and others:
            g = others[0].availableGeometry()
            self.move(g.left() + 24, g.top() + 24)
            return
        g = primary.geometry()
        self.move(g.left() + 12, g.top() + int(g.height() * 0.30))

    def _fade_out(self):
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(350)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.hide)
        self._fade.start()


# ---------------------------------------------------------------------------
# taskbar panel
# ---------------------------------------------------------------------------

class TaskbarPanel(QWidget):
    MIN_W = 240

    DRAG_START = 5   # pixels of movement before a press counts as a drag

    def __init__(self, on_open, on_recap, on_quit, saved_pos=None,
                 on_moved=None):
        super().__init__(None, FLOAT_FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.on_open = on_open
        self.on_moved = on_moved
        self.menu_open = False
        self.dragging = False
        self._press = None
        self._shown = None
        # Where the user dragged it: (centre x, top y), kept as the centre so
        # the pill grows evenly both ways when its text gets longer.
        self.custom = saved_pos if self._valid(saved_pos) else None
        self.menu = rounded_menu()
        self.menu.addAction("Open Turbo Tracker", on_open)
        self.menu.addAction("Show last recap", on_recap)
        self.menu.addAction("Move back to the taskbar", self.reset_position)
        # Shown only when a newer release exists (main window may be hidden
        # in panel mode, so its banner alone could go unseen).
        self._on_update = None
        self.update_action = self.menu.addAction(
            "Update available", lambda: self._on_update and self._on_update())
        self.update_action.setVisible(False)
        self.menu.addSeparator()
        self.menu.addAction("Quit", on_quit)
        self.menu.aboutToHide.connect(lambda: setattr(self, "menu_open", False))

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 14, 0)
        row.setSpacing(10)
        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        self.left = label("")
        self.left.setStyleSheet("font-size: 12px; font-weight: 700;")
        self.right = label("")
        row.addWidget(self.dot)
        row.addWidget(self.left)
        row.addWidget(self.right)
        self.setCursor(Qt.PointingHandCursor)
        self.show_text("Today 0-0", "no games yet", SUBTLE, ACCENT)
        self.show()
        winutil.pin_topmost(int(self.winId()))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(tint(SURFACE, 240))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)

    def show_text(self, left, right, color, dot=ACCENT):
        if self._shown == (left, right, color, dot):
            return
        self._shown = (left, right, color, dot)
        self.left.setText(left)
        self.right.setText(right)
        self.right.setStyleSheet(f"font-size: 12px; color: {color};")
        self.dot.setStyleSheet(f"background: {dot}; border-radius: 4px;")
        self.adjustSize()
        self._place()

    @staticmethod
    def _valid(pos):
        """A saved (x, y) that is two real ints on some screen right now.
        bool is a subclass of int, so rule it out explicitly."""
        if not (isinstance(pos, (list, tuple)) and len(pos) == 2
                and all(isinstance(v, int) and not isinstance(v, bool)
                        for v in pos)):
            return False
        return QGuiApplication.screenAt(QPoint(pos[0], pos[1] + 8)) is not None

    def set_update(self, version, on_click):
        self._on_update = on_click if version else None
        self.update_action.setVisible(bool(version))
        if version:
            self.update_action.setText(f"Download update {version}")

    def reset_position(self):
        self.custom = None
        self._place()
        if self.on_moved:
            self.on_moved(None)

    def _place(self):
        """Where the user dragged it, else on the taskbar just left of the
        tray icons."""
        full, work, dpr = primary_areas()
        w = max(self.MIN_W, self.sizeHint().width())
        if self.custom:
            h = 32
            self.setGeometry(self.custom[0] - w // 2, self.custom[1], w, h)
            return
        bar_h = full.bottom() - work.bottom()
        if bar_h >= 24:                          # taskbar along the bottom
            h = min(32, bar_h - 10)
            px = winutil.notify_area_left_px()
            right = int(px / dpr) if px else full.right() - 220
            if right < full.left() + w:
                right = full.right() - 220
            self.setGeometry(right - w - 10,
                             work.bottom() + 1 + (bar_h - h) // 2, w, h)
        else:                                    # fallback: above it
            self.setGeometry(work.right() - w - 16, work.bottom() - 48, w, 34)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.menu_open = True
            at = event.globalPosition().toPoint()
            h = self.menu.sizeHint().height()
            up = at - QPoint(0, h + 8)
            self.menu.popup(up if up.y() >= 0 else at + QPoint(0, 8))
        elif event.button() == Qt.LeftButton:
            # Remember where the press landed; a click opens the app, a
            # drag moves the pill (decided in mouseMove / mouseRelease).
            self._press = (event.globalPosition().toPoint(), self.pos())

    def mouseMoveEvent(self, event):
        if not self._press:
            return
        start, origin = self._press
        delta = event.globalPosition().toPoint() - start
        if not self.dragging and delta.manhattanLength() < self.DRAG_START:
            return
        self.dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        self.move(origin + delta)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._press:
            return
        self._press = None
        if not self.dragging:
            self.on_open()
            return
        self.dragging = False
        self.setCursor(Qt.PointingHandCursor)
        # Keep it on screen, then remember it as (centre x, top y).
        g = self.geometry()
        screen = QGuiApplication.screenAt(g.center()) or \
            QGuiApplication.primaryScreen()
        area = screen.geometry()
        x = max(area.left(), min(g.left(), area.right() - g.width() + 1))
        y = max(area.top(), min(g.top(), area.bottom() - g.height() + 1))
        self.custom = [x + g.width() // 2, y]
        self._place()
        if self.on_moved:
            self.on_moved(self.custom)
