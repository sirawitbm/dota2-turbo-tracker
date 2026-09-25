"""Turbo Tracker widgets (PySide6): theme, main window, recap card, panel.

No game logic here - turbo_tracker.py feeds these widgets plain dicts.
"""

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRect,
                            QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QGuiApplication,
                           QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap, QStandardItem,
                           QStandardItemModel)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                               QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QListView, QMenu, QPushButton,
                               QSizePolicy, QStackedWidget, QStyle,
                               QStyledItemDelegate, QVBoxLayout, QWidget)

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
        self.resize(1080, 720)
        self.setMinimumSize(920, 560)

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
        self.banner_btn = button("Set up now", "primary", ctl.run_setup)
        brow.addWidget(self.banner_btn)
        self.banner.hide()
        root.addWidget(self.banner)

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
        foot.addStretch()
        foot.addWidget(button("Show last recap", "ghost", ctl.show_last_recap))
        root.addLayout(foot)

    def _switch_tab(self, key):
        self.pages.setCurrentIndex(0 if key == "matches" else 1)

    def set_banner(self, text, show_button):
        if not text:
            self.banner.hide()
            return
        self.banner_text.setText(text)
        self.banner_btn.setVisible(show_button)
        self.banner.show()

    def showEvent(self, event):
        super().showEvent(event)
        winutil.dark_title_bar(int(self.winId()))

    def closeEvent(self, event):
        event.ignore()
        self.closed.emit()


# ---------------------------------------------------------------------------
# floating windows shared bits
# ---------------------------------------------------------------------------

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
            right = anchor.geometry().right() + m
            x = min(right - self.width() + 1, work.right() - self.width() + m)
        else:
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
# taskbar panel
# ---------------------------------------------------------------------------

class TaskbarPanel(QWidget):
    MIN_W = 240

    def __init__(self, on_open, on_recap, on_quit):
        super().__init__(None, FLOAT_FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.on_open = on_open
        self.menu_open = False
        self._shown = None
        self.menu = QMenu()
        self.menu.setWindowFlags(self.menu.windowFlags()
                                 | Qt.FramelessWindowHint
                                 | Qt.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WA_TranslucentBackground)
        self.menu.addAction("Open Turbo Tracker", on_open)
        self.menu.addAction("Show last recap", on_recap)
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

    def _place(self):
        """On the taskbar, right edge just left of the tray icons."""
        full, work, dpr = primary_areas()
        w = max(self.MIN_W, self.sizeHint().width())
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
            self.menu.popup(event.globalPosition().toPoint()
                            - QPoint(0, self.menu.sizeHint().height() + 8))
        else:
            self.on_open()
