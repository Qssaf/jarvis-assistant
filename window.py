"""Jarvis's app window: native Qt, built once at startup and only shown or hidden, so it opens instantly.
Home is the conversation (under the arc reactor) beside a Today column; everything else is a page in the left rail."""
import math, os, queue, re, threading, time
from html import escape
from urllib.parse import quote

import requests
from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QCompleter, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

import store
from icons import svg_icon

# ---------------------------------------------------------------- the look: the first Jarvis UI's colours (cyan, orange, deep navy)
BG, RAIL, SURFACE, RAISED, BORDER = "#04080d", "#050b11", "#0a1621", "#0e1e2b", "#16364a"
TEXT, DIM, FAINT = "#d6f3ff", "#6d8a9b", "#4a6373"
GOLD, CYAN, RED, GREEN, VIOLET = "#ff9d3f", "#3fd8ff", "#f87171", "#4ade80", "#a78bfa"  # (GOLD is the orange now)
MONO = "\"JetBrainsMono Nerd Font\", \"Cascadia Mono\", Consolas, \"DejaVu Sans Mono\", monospace"
STATES = {"idle": ("Ready", CYAN, 'Say "Hey Jarvis", or type below'), "listening": ("Listening", CYAN, "Go ahead, I'm listening"),
          "speaking": ("Speaking", CYAN, 'Say "Hey Jarvis" to cut in'), "thinking": ("Working", GOLD, "On it")}
PAGES = [("home", "Home", "home"), ("sessions", "Chats", "chats"), ("activity", "Activity", "activity"),
         ("connections", "Accounts", "accounts"), ("plugins", "Plugins", "plugins"), ("memory", "Memory", "memory"),
         ("settings", "Settings", "settings")]
QUICK = [("sun", "Good morning", "Your day at a glance"), ("calendar", "What's due this week?", "From Google Classroom"),
         ("mail", "How many unread emails do I have?", "Gmail"), ("screen", "What's on my screen?", "Jarvis looks for you"),
         ("timer", "Set a 10 minute timer", "With a notification"), ("image", "Make a picture of a cozy rainy city at night", "Image generation")]
ACCOUNT_MODES = [("ask", "Ask before changes"), ("full", "Full access"), ("read_only", "Read only"), ("paused", "Paused")]
PRESETS = [("Notion (official)", "notion", "url", "https://mcp.notion.com/mcp"),
           ("Docs lookup (Context7)", "context7", "url", "https://mcp.context7.com/mcp"),
           ("Files in my home folder", "files", "command", "npx -y @modelcontextprotocol/server-filesystem ~"),
           ("Headless browser (Playwright)", "playwright", "command", "npx -y @playwright/mcp@latest --headless")]
CARD_BG = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(12,32,46,.85), stop:1 rgba(8,20,30,.85))"

QSS = f"""
QMainWindow, #root, #page {{ background: {BG}; }}
#home {{ background: qradialgradient(cx:0.42, cy:0.0, radius:0.85, fx:0.42, fy:0.0, stop:0 #0b2333, stop:0.6 #060d14, stop:1 {BG}); }}
QWidget {{ color: {TEXT}; font-size: 10pt; }}
#rail {{ background: {RAIL}; border-right: 1px solid rgba(63,216,255,.14); }}
QToolButton#nav {{ border: none; border-radius: 14px; padding: 6px 2px 4px; color: {FAINT}; background: transparent; font-size: 7.5pt; }}
QToolButton#nav:hover {{ color: {TEXT}; background: rgba(63,216,255,.06); }}
QToolButton#nav[active="true"] {{ color: {CYAN}; background: rgba(63,216,255,.10); }}
#title {{ font-size: 16pt; font-weight: 700; }}
#subtitle, #dim {{ color: {DIM}; }}
#faint {{ color: {FAINT}; }}
#small {{ color: {DIM}; font-size: 8.5pt; }}
#err {{ color: {RED}; }}
#clock {{ font-family: {MONO}; font-size: 11pt; color: {DIM}; }}
#hero {{ font-size: 24pt; font-weight: 700; }}
#heroHint {{ color: {DIM}; font-size: 11pt; }}
#state {{ font-size: 11pt; font-weight: 700; }}
#card {{ background: {CARD_BG}; border: 1px solid rgba(63,216,255,.14); border-radius: 18px; }}
#cardTitle {{ color: {FAINT}; font-size: 7.5pt; font-weight: 700; letter-spacing: 1.6px; }}
#big {{ font-family: {MONO}; font-size: 20pt; }}
#huge {{ font-size: 28pt; font-weight: 300; }}
#section {{ font-size: 11pt; font-weight: 700; padding-top: 6px; }}
#you {{ background: rgba(255,157,63,.10); border: 1px solid rgba(255,157,63,.32); border-radius: 18px; border-bottom-right-radius: 6px; }}
#who {{ color: {CYAN}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
#reply {{ font-size: 10.5pt; line-height: 140%; }}
#tool {{ color: {DIM}; font-size: 8.5pt; }}
#notice {{ color: {FAINT}; font-size: 8.5pt; }}
#thinking {{ background: rgba(167,139,250,.06); border-left: 2px solid {VIOLET}; border-radius: 4px; }}
#thinkingText {{ color: #c4b6fb; font-size: 9pt; font-style: italic; }}
#imageCard {{ background: {SURFACE}; border: 1px solid rgba(63,216,255,.14); border-radius: 16px; }}
#composer {{ background: rgba(10,26,38,.92); border: 1px solid rgba(63,216,255,.28); border-radius: 22px; }}
#composer QLineEdit {{ background: transparent; border: none; font-size: 10.5pt; padding: 8px 4px; }}
#attachment {{ background: {RAISED}; border-radius: 10px; padding: 4px 10px; color: {DIM}; font-size: 8.5pt; }}
QPushButton {{ background: transparent; border: 1px solid rgba(63,216,255,.28); color: {CYAN}; border-radius: 12px; padding: 8px 15px; }}
QPushButton:hover {{ background: rgba(63,216,255,.10); border-color: {CYAN}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {BORDER}; }}
QPushButton#primary {{ background: {CYAN}; color: #03131c; border: none; font-weight: 700; }}
QPushButton#primary:hover {{ background: #7ce6ff; }}
QPushButton#danger {{ background: transparent; color: {RED}; border: 1px solid rgba(248,113,113,.35); }}
QPushButton#danger:hover {{ background: rgba(248,113,113,.12); }}
QPushButton#primary:disabled, QPushButton#danger:disabled {{ background: transparent; color: {FAINT}; border: 1px solid {BORDER}; }}
QPushButton#link {{ background: transparent; border: none; color: {DIM}; padding: 2px 0; text-align: left; }}
QPushButton#link:hover {{ color: {CYAN}; }}
QPushButton#chip {{ text-align: left; background: rgba(63,216,255,.05); border: 1px solid rgba(63,216,255,.22); border-radius: 12px; padding: 8px 12px; color: {TEXT}; }}
QPushButton#chip:hover {{ border-color: {CYAN}; color: {CYAN}; }}
QPushButton#suggest {{ text-align: left; background: {CARD_BG}; border: 1px solid rgba(63,216,255,.16); border-radius: 16px;
                       padding: 14px 16px; font-size: 10pt; color: {TEXT}; }}
QPushButton#suggest:hover {{ border-color: {CYAN}; background: rgba(63,216,255,.08); }}
QToolButton#icon {{ border: none; border-radius: 18px; background: transparent; }}
QToolButton#icon:hover {{ background: {RAISED}; }}
QToolButton#send {{ border: none; border-radius: 18px; background: {CYAN}; }}
QToolButton#send:hover {{ background: #7ce6ff; }}
QToolButton#stop {{ border: none; border-radius: 18px; background: rgba(248,113,113,.14); }}
QToolButton#stop:hover {{ background: rgba(248,113,113,.26); }}
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: rgba(4,16,24,.85); border: 1px solid rgba(63,216,255,.22);
    border-radius: 12px; padding: 8px 11px; selection-background-color: {CYAN}; selection-color: #03131c; }}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {CYAN}; }}
QLineEdit#search {{ border-radius: 17px; padding: 8px 16px; background: rgba(4,16,24,.7); border: 1px solid rgba(63,216,255,.18); }}
QLineEdit#search:focus {{ border-color: {CYAN}; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; selection-background-color: rgba(63,216,255,.20); border: 1px solid {BORDER}; }}
QTextBrowser, QListWidget, QScrollArea {{ background: transparent; border: none; }}
#chatInner, #todayInner, #pageInner, #heroBox {{ background: transparent; }}
QListWidget::item {{ padding: 10px 12px; border-radius: 12px; margin: 1px 0; }}
QListWidget::item:selected, QListWidget::item:hover {{ background: rgba(63,216,255,.08); color: {TEXT}; }}
QProgressBar {{ background: rgba(63,216,255,.08); border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {GOLD}); }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba(63,216,255,.20); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 6px; border: 1px solid {BORDER}; background: {RAISED}; }}
QCheckBox::indicator:checked {{ background: {CYAN}; border-color: {CYAN}; }}
QCheckBox::indicator:hover {{ border-color: {CYAN}; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
QMessageBox {{ background: {SURFACE}; }}
"""
PREVIEW_CSS = f"""p {{ margin: 0; }} .who {{ color: {CYAN}; font-size: 8pt; margin-top: 12px; }} .you {{ color: {GOLD}; font-size: 8pt;
margin-top: 12px; }} .sys {{ color: {FAINT}; font-size: 9pt; margin-top: 8px; }} .tool {{ color: {DIM}; font-size: 9pt; margin-top: 4px; }}
a {{ color: {CYAN}; }}"""


# ---------------------------------------------------------------- plumbing
class Bridge(QObject):
    done = Signal(object, object)  # (callback, result): background results, delivered on the UI thread
    show = Signal()


bridge = Bridge()


def run(fn, then=None):
    """Run fn off the UI thread; then(result or exception) runs back on it."""
    def work():
        try:
            result = fn()
        except Exception as e:
            result = e
        if then:
            bridge.done.emit(then, result)
    threading.Thread(target=work, daemon=True).start()


def label(text, name=None, wrap=False, rich=False):
    w = QLabel(text)
    w.setTextFormat(Qt.RichText if rich else Qt.PlainText)  # text from plugins, accounts and the web is never markup
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text, fn, name=None, tip=None):
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(lambda *_: fn())
    return b


def icon_button(icon, fn, tip, name="icon", color=TEXT, size=36, glyph=18):
    b = QToolButton()
    b.setObjectName(name)
    b.setIcon(svg_icon(icon, color, glyph))
    b.setIconSize(QSize(glyph, glyph))
    b.setFixedSize(size, size)
    b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(lambda *_: fn())
    return b


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


def linkify(text):
    """Escaped text with links; very long words get break points so they wrap."""
    out = []
    for i, chunk in enumerate(re.split(r"(https?://[^\s<>)\]\"']+)", text)):
        if i % 2:
            out.append(f'<a style="color:{CYAN}" href="{escape(chunk, quote=True)}">{escape(chunk)}</a>')
        else:
            out.append(re.sub(r"(\S{40})", "\\1\u200b", escape(chunk)))
    return "".join(out).replace("\n", "<br>")


def message_html(m, tool_label):
    """A message as rich text, for the read-only previews of saved conversations."""
    who, text = m["who"], str(m["text"])
    if who == "tool":
        return f'<p class="tool">• {escape(tool_label(text))}</p>'
    if who == "image":
        return f'<p><img src="{QUrl.fromLocalFile(text).toString()}" width="260"></p>'
    if who in ("system", "thinking"):
        return f'<p class="sys">{linkify(text)}</p>'
    return f'<p class="{"you" if who == "you" else "who"}">{"YOU" if who == "you" else "JARVIS"}</p><p>{linkify(text)}</p>'


def card(title=None):
    """A soft rounded surface with an optional small caps title; returns (frame, its layout)."""
    frame = QFrame()
    frame.setObjectName("card")
    v = QVBoxLayout(frame)
    v.setContentsMargins(18, 16, 18, 18)
    v.setSpacing(10)
    if title:
        v.addWidget(label(title.upper(), "cardTitle"))
    return frame, v


def rounded(pixmap, radius=12):
    out = QPixmap(pixmap.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, pixmap.width(), pixmap.height()), radius, radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pixmap)
    p.end()
    return out


# ---------------------------------------------------------------- the arc reactor and the status light
class Reactor(QWidget):
    """Spinning rings round a breathing core: faster while listening or speaking, gold while working."""

    def __init__(self, size=140):
        super().__init__()
        self.setFixedSize(size, size)
        self.state = "idle"
        timer = QTimer(self)
        timer.timeout.connect(lambda: self.isVisible() and self.update())
        timer.start(33)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s, t, working = self.width(), time.time(), self.state == "thinking"
        color = QColor(GOLD if working else CYAN)
        mid = s / 2

        def ring(inset, width, period, starts, span, alpha=255, dashed=False):
            r = mid - inset - width / 2
            c = QColor(color)
            c.setAlpha(alpha)
            p.save()
            p.translate(mid, mid)
            p.rotate(t / period * 360 % 360)
            p.setPen(QPen(c, width, Qt.DashLine if dashed else Qt.SolidLine, Qt.RoundCap))
            for start in starts:
                p.drawArc(QRectF(-r, -r, 2 * r, 2 * r), int((start - span / 2) * 16), int(span * 16))
            p.restore()

        ring(0, max(1.5, s / 70), 1.2 if working else 9, (90, 270), 90)
        ring(s * 0.107, 1, -14, (0,), 360, alpha=100, dashed=True)
        ring(s * 0.213, max(1.5, s / 70), 1.2 if working else 6, (0, 180), 90)
        period = {"listening": 0.6, "speaking": 0.35}.get(self.state, 3.5)
        breath = 0.5 + 0.5 * math.cos(t / period * 2 * math.pi)
        core = (s / 2 - s * 0.347) * (0.88 + 0.12 * breath)
        glow = QRadialGradient(mid, mid, core * (2.6 if self.state == "listening" else 2.0))
        halo = QColor(color)
        halo.setAlpha(int(70 + 40 * breath))
        glow.setColorAt(0, halo)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(0, 0, s, s))
        g = QRadialGradient(mid, mid, core)
        g.setColorAt(0, QColor(255, 255, 255, int(255 * (0.75 + 0.25 * breath))))
        g.setColorAt(0.35, color)
        faint = QColor(color)
        faint.setAlpha(40)
        g.setColorAt(0.97, faint)
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(g)
        p.drawEllipse(QRectF(mid - core, mid - core, 2 * core, 2 * core))


class Orb(QWidget):
    """A small glowing light: Jarvis's avatar in the chat, and its state in the rail."""

    def __init__(self, size, on_click=None, pulse=True):
        super().__init__()
        self.setFixedSize(size, size)
        self.state, self.on_click, self.pulse = "idle", on_click, pulse
        if on_click:
            self.setCursor(Qt.PointingHandCursor)
        if pulse:
            timer = QTimer(self)
            timer.timeout.connect(lambda: self.isVisible() and self.update())
            timer.start(40)

    def mousePressEvent(self, e):
        if self.on_click:
            self.on_click()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        color = QColor(STATES.get(self.state, STATES["idle"])[1])
        speed = {"listening": 6, "speaking": 12, "thinking": 4}.get(self.state, 1.5)
        pulse = 0.5 + 0.5 * math.sin(time.time() * speed) if self.pulse else 0.6
        glow = QRadialGradient(s / 2, s / 2, s / 2)
        glow.setColorAt(0, QColor(255, 255, 255))
        glow.setColorAt(0.3, color)
        edge = QColor(color)
        edge.setAlpha(int(40 + 90 * pulse))
        glow.setColorAt(0.7, edge)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(0, 0, s, s))


class Clickable(QLabel):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        self.fn()


# ---------------------------------------------------------------- the conversation
class ChatView(QScrollArea):
    """Your messages in soft bubbles on the right; Jarvis's replies as clean text beside its orb, with tool use, pictures
    and (if switched on) its thinking tucked under it."""

    INDENT = 40  # where Jarvis's text starts, past its orb

    def __init__(self, tool_label):
        super().__init__()
        self.tool_label, self.show_thinking = tool_label, False
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("chatInner")
        self.box = QVBoxLayout(inner)
        self.box.setContentsMargins(4, 8, 14, 8)
        self.box.setSpacing(12)
        self.box.addStretch(1)  # messages settle at the bottom, like any chat
        self.setWidget(inner)
        self.sized, self.last_tool, self.follow, self.last_who = [], None, True, None
        bar = self.verticalScrollBar()
        bar.rangeChanged.connect(lambda lo, hi: self.follow and bar.setValue(hi))  # stick to the newest message...
        bar.valueChanged.connect(lambda v: setattr(self, "follow", v >= bar.maximum() - 40))  # ...unless you scrolled up

    def clear(self):
        while self.box.count() > 1:
            item = self.box.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.sized, self.last_tool, self.last_who = [], None, None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for w in self.sized:
            self.fit(w)

    def max_width(self):
        return max(280, int(self.viewport().width() * 0.74))

    def fit(self, w):
        """As wide as its text, up to most of the chat's width (a wrapping label alone picks a narrow width)."""
        w.setMaximumWidth(self.max_width())
        body = getattr(w, "body", None)
        if body is not None:
            body.ensurePolished()  # measured once it's in the window, so with the chat's font size
            natural = max((body.fontMetrics().horizontalAdvance(line) for line in body.raw.split("\n")), default=0) + 10
            body.setMinimumWidth(min(natural, self.max_width() - 32))

    def _text(self, text, name):
        body = label(linkify(text), name, wrap=True, rich=True)
        body.setTextInteractionFlags(Qt.TextBrowserInteraction)
        body.setOpenExternalLinks(True)
        body.raw = text
        return body

    def add(self, m):
        who, text = m["who"], str(m["text"])
        if who == "thinking" and not self.show_thinking:
            return
        if who == "tool":
            name = self.tool_label(text)
            if self.last_tool and self.last_tool[0] == name:  # the same tool again: one line, counted
                self.last_tool[2] += 1
                self.last_tool[1].setText(f'<span style="color:{GOLD}">●</span>&nbsp; {escape(name)}&nbsp; ×{self.last_tool[2]}')
                return
            line = label(f'<span style="color:{GOLD}">●</span>&nbsp; {escape(name)}', "tool", rich=True)
            line.setToolTip(text)
            self._jarvis_row(line)
            self.last_tool = [name, line, 1]
            return
        self.last_tool = None
        if who == "you":
            frame = QFrame()
            frame.setObjectName("you")
            v = QVBoxLayout(frame)
            v.setContentsMargins(15, 10, 15, 11)
            frame.body = self._text(text, "reply")
            v.addWidget(frame.body)
            self.fit(frame)
            self.sized.append(frame)
            row = QHBoxLayout()
            row.setContentsMargins(0, 6, 0, 0)
            row.addStretch(1)
            row.addWidget(frame)
            self._add_row(row)
        elif who == "jarvis":
            col = QWidget()
            v = QVBoxLayout(col)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(3)
            v.addWidget(label("JARVIS", "who"))
            col.body = self._text(text, "reply")
            v.addWidget(col.body)
            self.fit(col)
            self.sized.append(col)
            self._jarvis_row(col, avatar=True)
        elif who == "image":
            self._jarvis_row(self._image(text, m.get("caption", "")))
        elif who == "thinking":
            frame = QFrame()
            frame.setObjectName("thinking")
            v = QVBoxLayout(frame)
            v.setContentsMargins(12, 7, 12, 8)
            short = text if len(text) < 320 else text[:300].rsplit(" ", 1)[0] + "…"
            body = label(short, "thinkingText", wrap=True)
            v.addWidget(body)
            if short != text:
                more = button("Show all", lambda: (body.setText(text), more.hide()), "link")
                v.addWidget(more)
            frame.setMaximumWidth(self.max_width())
            self._jarvis_row(frame)
        else:  # notices
            notice = label(text, "notice", wrap=True)
            notice.setAlignment(Qt.AlignCenter)
            self.box.addWidget(notice)
        self.last_who = who
        self.scroll_down()

    def _jarvis_row(self, widget, avatar=False):
        """Jarvis's side: its orb, then the content; tool lines, pictures and thinking line up under its text."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        if avatar:
            orb = Orb(28, pulse=False)
            row.addWidget(orb, 0, Qt.AlignTop)
        else:
            row.addSpacing(self.INDENT)
        row.addWidget(widget)
        row.addStretch(1)
        self._add_row(row)

    def _add_row(self, row):
        holder = QWidget()
        holder.setLayout(row)
        self.box.addWidget(holder)
        for w in self.sized[-1:]:
            self.fit(w)

    def _image(self, path, caption):
        frame = QFrame()
        frame.setObjectName("imageCard")
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 8, 8, 10)
        pix = QPixmap(path)
        pic = Clickable(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        pic.setToolTip(f"{path}\nClick to open")
        if pix.isNull():
            pic.setText(f"(couldn't load {os.path.basename(path)})")
        else:
            pic.setPixmap(rounded(pix.scaled(460, 340, Qt.KeepAspectRatio, Qt.SmoothTransformation), 10))
        v.addWidget(pic)
        if caption:
            v.addWidget(label(caption, "small", wrap=True))
        return frame

    def scroll_down(self):
        self.follow = True
        QTimer.singleShot(30, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))


# ---------------------------------------------------------------- the window
class Window(QMainWindow):
    def __init__(self, get, post, state, tool_label, icon, started):
        super().__init__()
        self.get, self.post, self.tool_label, self.started = get, post, tool_label, started
        self.events = queue.Queue()  # app events (messages, state changes), fed by jarvis.emit
        self.msgs, self.state, self.tools_total, self.attached, self.selected = [], state, 0, [], None
        self.setWindowTitle("J.A.R.V.I.S.")
        self.setWindowIcon(icon)
        self.setAcceptDrops(True)  # drop files on the window to attach them
        room = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1400, int(room.width() * 0.92)), min(880, int(room.height() * 0.92)))
        self.setStyleSheet(QSS)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._rail(icon))
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.stack = QStackedWidget()
        builders = {"home": self._home, "sessions": self._sessions, "activity": self._activity, "connections": self._connections,
                    "plugins": self._plugins, "memory": self._memory, "settings": self._settings}
        self.pages = {}
        for key, *_ in PAGES:
            self.pages[key] = builders[key]()
            self.stack.addWidget(self.pages[key])
        main.addWidget(self.stack, 1)
        h.addLayout(main, 1)
        self.loaders = {"sessions": self.load_sessions, "connections": self.load_connections, "plugins": self.load_plugins,
                        "settings": self.load_settings, "memory": lambda: (self.load_memory(), self.load_reminders())}

        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(self.focus_search)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.new_conversation)
        bridge.show.connect(self.present)  # (bound to the window, so they run on the UI thread)
        bridge.done.connect(self._deliver)
        self.chat.show_thinking = store.settings()["show_thinking"]
        self.go("home")
        self.reload_chat()
        self.load_today()
        self.load_reminders()
        self.load_memory()
        self.set_state(state)
        for every, fn in ((60, self.drain), (1000, self.tick), (60000, self.load_reminders), (600000, self.load_today),
                          (3000, self.load_live)):
            t = QTimer(self)
            t.timeout.connect(fn)
            t.start(every)
        self.tick()

    # ---- frame
    def _rail(self, icon):
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(80)
        v = QVBoxLayout(rail)
        v.setContentsMargins(8, 18, 8, 18)
        v.setSpacing(4)
        logo = QLabel()
        logo.setPixmap(icon.pixmap(36, 36))
        logo.setAlignment(Qt.AlignCenter)
        logo.setToolTip("J.A.R.V.I.S.")
        v.addWidget(logo)
        v.addSpacing(18)
        self.nav = {}
        for key, title, glyph in PAGES:
            b = QToolButton()
            b.setObjectName("nav")
            b.setText(title)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setIconSize(QSize(22, 22))
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(64, 58)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            b.glyph = glyph
            self.nav[key] = b
            v.addWidget(b, 0, Qt.AlignHCenter)
        v.addStretch()
        self.orb = Orb(28, self.talk_or_stop)
        self.orb.setToolTip("Click to talk, or to stop")
        v.addWidget(self.orb, 0, Qt.AlignHCenter)
        return rail

    def topbar(self, title=None, hint=""):
        """A page's header: its title (or, on Home, the date), the Ctrl+K box and the time."""
        bar = QWidget()
        h = QGridLayout(bar)  # three columns, the outer two equally wide, so the search box is truly centred
        h.setContentsMargins(28, 16, 28, 8)
        h.setHorizontalSpacing(18)
        h.setColumnStretch(0, 1)
        h.setColumnStretch(2, 1)
        left = QVBoxLayout()
        left.setSpacing(1)
        if title:
            left.addWidget(label(title, "title"))
        sub = label(hint, "subtitle", wrap=True)
        left.addWidget(sub)
        h.addLayout(left, 0, 0)
        search = QLineEdit()
        search.setObjectName("search")
        search.setPlaceholderText("Ask Jarvis, or jump to a page   ·   Ctrl K")
        search.setFixedWidth(400)
        search.addAction(svg_icon("search", FAINT, 16), QLineEdit.LeadingPosition)
        done = QCompleter([p[1] for p in PAGES], search)
        done.setCaseSensitivity(Qt.CaseInsensitive)
        done.setFilterMode(Qt.MatchContains)
        done.activated[str].connect(lambda text: QTimer.singleShot(0, lambda: self.command(text, search)))
        search.setCompleter(done)
        search.returnPressed.connect(lambda: self.command(search.text(), search))
        h.addWidget(search, 0, 1, Qt.AlignVCenter)
        right = QHBoxLayout()
        right.setSpacing(14)
        right.addStretch(1)
        toast, clock = label("", "small"), label("", "clock")
        right.addWidget(toast)
        if not title:  # Home: a new conversation is always one click away
            new = QPushButton("  New chat")
            new.setIcon(svg_icon("plus", CYAN, 16))
            new.setCursor(Qt.PointingHandCursor)
            new.setToolTip("Start a new conversation (Ctrl+N)")
            new.clicked.connect(lambda *_: self.new_conversation())
            right.addWidget(new)
        right.addWidget(clock)
        h.addLayout(right, 0, 2)
        self.searches = getattr(self, "searches", []) + [search]
        self.clocks = getattr(self, "clocks", []) + [(clock, sub if not title else None)]
        self.toasts = getattr(self, "toasts", []) + [toast]
        return bar

    def page(self, title, hint=""):
        """A page: its header and a scrolling, centred, width-limited column; returns (page widget, column layout)."""
        page = QWidget()
        page.setObjectName("page")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.topbar(title, hint))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner.setObjectName("pageInner")
        row = QHBoxLayout(inner)
        row.setContentsMargins(28, 12, 28, 28)
        column = QVBoxLayout()
        column.setSpacing(14)
        holder = QWidget()
        holder.setMaximumWidth(1080)
        holder.setLayout(column)
        row.addWidget(holder, 1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return page, column

    def go(self, key):
        self.current = key
        self.stack.setCurrentWidget(self.pages[key])
        for k, b in self.nav.items():
            b.setProperty("active", k == key)
            b.setIcon(svg_icon(b.glyph, CYAN if k == key else FAINT, 22))
            b.style().unpolish(b)
            b.style().polish(b)
        if key in self.loaders:
            self.loaders[key]()
        if key == "home":
            self.ask.setFocus()

    def focus_search(self):
        search = self.searches[list(self.pages).index(self.current)]
        search.setFocus()
        search.selectAll()

    def command(self, text, search):
        text = text.strip()
        search.clear()
        match = next((k for k, t, _ in PAGES if t.lower() == text.lower()), None)
        if match:
            self.go(match)
        elif text:
            self.send(text)

    def present(self):
        self.load_today()
        self.showNormal() if self.isMinimized() else self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.load_live)

    def _deliver(self, then, result):
        then(result)

    def closeEvent(self, e):  # closing only hides: Jarvis keeps running in the tray
        e.ignore()
        self.hide()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.attach([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])
        self.go("home")

    def toast(self, text, bad=False):
        for t in self.toasts:
            t.setText(text)
            t.setStyleSheet(f"color: {RED if bad else DIM}")
        QTimer.singleShot(7000 if bad else 4000, lambda: [t.setText("") for t in self.toasts if t.text() == text])

    def call(self, path, data=None, then=None):
        """GET (data None) or POST the local API off the UI thread; errors become a toast."""
        def done(result):
            if isinstance(result, Exception):
                self.toast(str(result) or type(result).__name__, True)
            elif then:
                then(result)
        run(lambda: self.get(path) if data is None else self.post(path, data), done)

    # ---- live updates
    def drain(self):
        while True:
            try:
                d = self.events.get_nowait()
            except queue.Empty:
                return
            if d["kind"] == "state":
                self.set_state(d["state"])
            elif d["kind"] == "log":
                self.add_message({**{k: v for k, v in d.items() if k != "kind"}, "time": time.time()})

    def set_state(self, s):
        self.state = s
        name, color, hint = STATES.get(s, STATES["idle"])
        self.orb.state = self.reactor.state = self.small_reactor.state = s
        for lab in (self.state_label, self.hero_state):
            lab.setText(name)
            lab.setStyleSheet(f"color: {color};")
        self.state_hint.setText(hint)

    def talk_or_stop(self):
        self.call("/api/listen" if self.state == "idle" else "/api/stop", {})

    def tick(self):
        for clock, sub in self.clocks:
            clock.setText(time.strftime("%H:%M"))
            if sub is not None:
                sub.setText(time.strftime("%A, %d %B"))
        hour = time.localtime().tm_hour
        self.greeting.setText("Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening")
        up = int(time.time() - self.started)
        self.tiles["Uptime"].setText(f"{up // 3600}h {up % 3600 // 60}m" if up >= 3600 else f"{up // 60}m")

    def add_message(self, m):
        self.msgs.append(m)
        self.chat.add(m)
        if m["who"] == "tool":
            self._activity_row(m)
        if (m["who"] == "tool" and re.search(r"reminder|remember|forget", str(m["text"]))) or str(m["text"]).startswith(("⏰", "📚")):
            QTimer.singleShot(800, self.load_reminders)
            QTimer.singleShot(800, self.load_memory)
        self.update_stats()

    def reload_chat(self):
        def show(conv):
            self.msgs = []
            self.chat.clear()
            self.activity.clear()
            for m in conv["messages"]:
                self.add_message(m)
            self.update_stats()
        self.call("/api/conversation", then=show)

    def update_stats(self):
        tools = [m for m in self.msgs if m["who"] == "tool"]
        self.tiles["Turns"].setText(str(sum(m["who"] == "you" for m in self.msgs)))
        self.tiles["Tools run"].setText(str(len(tools)))
        self.activity_empty.setVisible(not tools)
        talking = any(m["who"] in ("you", "jarvis") for m in self.msgs)
        self.hero.setVisible(not talking)  # a fresh conversation gets the big reactor and suggestions
        self.convo.setVisible(talking)

    def send(self, text):
        if self.attached:  # files ride along as paths; Jarvis reads them with read_file
            text = (text or "Have a look at this.") + "\n" + "\n".join(f"(attached: {p})" for p in self.attached)
            self.attached = []
            self.show_attachments()
        if text:
            self.call("/api/ask", {"text": text})
        if self.current != "home":
            self.go("home")

    def new_conversation(self):
        def fresh(_):
            self.reload_chat()
            self.load_sessions()
            self.go("home")
            self.toast("New conversation")
        self.call("/api/new", {}, fresh)

    # ---- home: the conversation and the Today column
    def _home(self):
        w = QWidget()
        w.setObjectName("home")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.topbar(None))
        h = QHBoxLayout()
        h.setContentsMargins(28, 4, 22, 22)
        h.setSpacing(22)
        center = QVBoxLayout()
        center.setSpacing(10)

        self.hero = QWidget()  # a fresh conversation: the reactor front and centre, a greeting, things to try
        self.hero.setObjectName("heroBox")
        hv = QVBoxLayout(self.hero)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.setSpacing(6)
        hv.addStretch(2)
        self.reactor = Reactor(170)
        hv.addWidget(self.reactor, 0, Qt.AlignHCenter)
        hv.addSpacing(10)
        self.greeting = label("", "hero")
        self.greeting.setAlignment(Qt.AlignCenter)
        hv.addWidget(self.greeting)
        self.hero_state = label("", "state")
        self.hero_state.setAlignment(Qt.AlignCenter)
        hv.addWidget(self.hero_state)
        hint = label('Say "Hey Jarvis", or type below. Drop a file here to ask about it.', "heroHint")
        hint.setAlignment(Qt.AlignCenter)
        hv.addWidget(hint)
        hv.addSpacing(22)
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (glyph, text, sub) in enumerate(QUICK):
            b = QPushButton(f"  {text}\n  {sub}")
            b.setObjectName("suggest")
            b.setIcon(svg_icon(glyph, CYAN, 20))
            b.setIconSize(QSize(20, 20))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=text: self.send(t))
            grid.addWidget(b, i // 3, i % 3)
        holder = QWidget()
        holder.setMaximumWidth(860)
        holder.setLayout(grid)
        hv.addWidget(holder, 0, Qt.AlignHCenter)
        hv.addStretch(3)
        center.addWidget(self.hero, 1)

        self.convo = QWidget()  # the conversation, with a small reactor showing the state
        cv = QVBoxLayout(self.convo)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(12)
        self.small_reactor = Reactor(54)
        head.addWidget(self.small_reactor)
        names = QVBoxLayout()
        names.setSpacing(0)
        self.state_label = label("", "state")
        self.state_hint = label("", "small")
        names.addStretch()
        names.addWidget(self.state_label)
        names.addWidget(self.state_hint)
        names.addStretch()
        head.addLayout(names)
        head.addStretch(1)
        cv.addLayout(head)
        self.chat = ChatView(self.tool_label)
        cv.addWidget(self.chat, 1)
        center.addWidget(self.convo, 1)
        self.convo.hide()

        center.addWidget(self._composer())
        h.addLayout(center, 1)
        h.addWidget(self._today())
        outer.addLayout(h, 1)
        return w

    def _composer(self):
        box = QFrame()
        box.setObjectName("composer")
        v = QVBoxLayout(box)
        v.setContentsMargins(10, 6, 8, 6)
        v.setSpacing(4)
        self.attach_row = QHBoxLayout()
        self.attach_row.setSpacing(6)
        v.addLayout(self.attach_row)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(icon_button("attach", self.pick_files, "Attach files (or drop them on the window)", color=DIM))
        self.ask = QLineEdit()
        self.ask.setPlaceholderText("Message Jarvis…")
        self.ask.returnPressed.connect(self._ask)
        row.addWidget(self.ask, 1)
        row.addWidget(icon_button("pause", lambda: self.call("/api/pause", {}), "Pause or resume listening (a reply or a task carries on)",
                                  color=DIM, glyph=16))
        row.addWidget(icon_button("stop", lambda: self.call("/api/stop", {}), "Stop: ends the task, the speech and the listening",
                                  "stop", RED, glyph=16))
        row.addWidget(icon_button("send", self._ask, "Send", "send", "#03131c", glyph=18))
        v.addLayout(row)
        return box

    def _ask(self):
        text = self.ask.text().strip()
        self.ask.clear()
        if text or self.attached:
            self.send(text)

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Attach files", os.path.expanduser("~"))
        self.attach(paths)

    def attach(self, paths):
        self.attached += [p for p in paths if p and p not in self.attached]
        self.show_attachments()

    def show_attachments(self):
        clear(self.attach_row)
        for p in self.attached:
            chip = Clickable(lambda p=p: (self.attached.remove(p), self.show_attachments()))
            chip.setObjectName("attachment")
            chip.setText(f"{os.path.basename(p)}   ✕")
            chip.setToolTip(f"{p}\nClick to remove")
            self.attach_row.addWidget(chip)
        if self.attached:
            self.attach_row.addStretch(1)

    def _today(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(318)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("todayInner")
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 4, 6, 4)
        v.setSpacing(12)

        music, m = card("Now playing")
        top = QHBoxLayout()
        top.setSpacing(12)
        self.art = QLabel()
        self.art.setFixedSize(56, 56)
        self.art.setStyleSheet(f"background: {RAISED}; border-radius: 10px;")
        top.addWidget(self.art)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.track, self.artist = label("Nothing playing", None), label("", "small")
        self.track.setStyleSheet("font-weight: 700;")
        info.addStretch()
        info.addWidget(self.track)
        info.addWidget(self.artist)
        info.addStretch()
        top.addLayout(info, 1)
        m.addLayout(top)
        controls = QHBoxLayout()
        controls.addStretch()
        media = lambda action: self.call(f"/api/media/{action}", {}, lambda _: self.load_live())
        self.play_btn = icon_button("play", lambda: media("PlayPause"), "Play / pause", glyph=18)
        for b in (icon_button("prev", lambda: media("Previous"), "Previous", glyph=16, color=DIM), self.play_btn,
                  icon_button("next", lambda: media("Next"), "Next", glyph=16, color=DIM)):
            controls.addWidget(b)
        controls.addStretch()
        m.addLayout(controls)
        self.art_url = ""
        v.addWidget(music)

        weather, wv = card("Weather")
        row = QHBoxLayout()
        self.wx_icon, self.wx_temp = label("", "huge"), label("…", "huge")
        row.addWidget(self.wx_icon)
        row.addWidget(self.wx_temp)
        row.addStretch()
        wv.addLayout(row)
        self.wx_text = label("", "small", wrap=True)
        wv.addWidget(self.wx_text)
        v.addWidget(weather)

        upnext, self.rem_box = card("Up next")
        self.rem_list = QVBoxLayout()
        self.rem_list.setSpacing(10)
        self.rem_box.addLayout(self.rem_list)
        v.addWidget(upnext)

        system, sv = card("System")
        self.bars = {}
        for name in ("CPU", "Memory", "Disk"):
            r = QHBoxLayout()
            r.addWidget(label(name, "small"))
            r.addStretch()
            value = label("", "small")
            r.addWidget(value)
            sv.addLayout(r)
            bar = QProgressBar()
            bar.setTextVisible(False)
            sv.addWidget(bar)
            self.bars[name] = (bar, value)
        v.addWidget(system)
        v.addStretch()
        scroll.setWidget(inner)
        return scroll

    def load_today(self):
        def show(t):
            self.tools_total = t.get("tools", 0)
            self.tiles["Tools available"].setText(str(self.tools_total))
            wx = t.get("weather")
            if wx:
                self.wx_icon.setText(wx["icon"])
                self.wx_temp.setText(wx["temp"])
                self.wx_text.setText(f"{wx['condition'].strip()} · feels {wx['feels']} · {wx['place']}")
            else:
                self.wx_temp.setText("—")
                self.wx_text.setText("Weather unavailable. Set your home city in Settings.")
        self.call("/api/today", then=show)

    def load_live(self):
        """Now playing and the system bars, every few seconds while the window is open."""
        if not self.isVisible():
            return
        def media(d):
            if not d:
                self.track.setText("Nothing playing")
                self.artist.setText("Start Spotify or any player")
                self.art.clear()
                return
            self.track.setText(d["title"] or "Unknown track")
            self.artist.setText(f"{d['artist']}  ·  {d['app']}" if d["artist"] else d["app"])
            self.play_btn.setIcon(svg_icon("pause" if d["status"] == "Playing" else "play", TEXT, 18))
            if d["art"].startswith("https://") and d["art"] != self.art_url:
                self.art_url = d["art"]
                run(lambda: requests.get(d["art"], timeout=8).content, self.show_art)
        def system(d):
            gib = 1024 ** 3
            for name, used, total, text in (("CPU", d["cpu"], 100, f"{d['cpu']:.0f}%"),
                                            ("Memory", d["mem_used"], d["mem_total"], f"{d['mem_used'] / gib:.1f} / {d['mem_total'] / gib:.0f} GB"),
                                            ("Disk", d["disk_used"], d["disk_total"], f"{d['disk_used'] / gib:.0f} / {d['disk_total'] / gib:.0f} GB")):
                bar, value = self.bars[name]
                bar.setValue(int(100 * used / max(1, total)))
                value.setText(text)
        self.call("/api/media", then=media)
        self.call("/api/system", then=system)

    def show_art(self, data):
        if isinstance(data, bytes):
            pix = QPixmap.fromImage(QImage.fromData(data)).scaled(56, 56, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.art.setPixmap(rounded(pix, 10))

    def load_reminders(self):
        def show(items):
            clear(self.rem_list)
            if not items:
                self.rem_list.addWidget(label('Nothing scheduled. Try "remind me in 20 minutes to stretch".', "small", wrap=True))
            for r in items[:5]:
                row = QHBoxLayout()
                txt = QVBoxLayout()
                txt.setSpacing(1)
                when = label(r["when"], None)
                when.setStyleSheet(f"color: {GOLD}; font-size: 8pt;")
                txt.addWidget(when)
                txt.addWidget(label(r["text"], wrap=True))
                row.addLayout(txt, 1)
                cancel = icon_button("close", lambda rid=r["id"]: self.call(f"/api/reminders/{rid}/cancel", {}, lambda _: self.load_reminders()),
                                     "Cancel this reminder", color=FAINT, size=26, glyph=14)
                row.addWidget(cancel, 0, Qt.AlignTop)
                self.rem_list.addLayout(row)
            if hasattr(self, "rem_manage"):
                self.show_reminders_page(items)
        self.call("/api/reminders", then=show)

    # ---- chats (saved sessions)
    def _sessions(self):
        page, col = self.page("Chats", "Every conversation is saved: search, read, continue or delete")
        top = QHBoxLayout()
        self.sess_search = QLineEdit()
        self.sess_search.setObjectName("search")
        self.sess_search.setPlaceholderText("⌕   Search all conversations…")
        self.sess_search.textChanged.connect(lambda _: self.sess_timer.start(250))
        self.sess_timer = QTimer(self)
        self.sess_timer.setSingleShot(True)
        self.sess_timer.timeout.connect(self.load_sessions)
        top.addWidget(self.sess_search, 1)
        top.addWidget(button("＋  New conversation", self.new_conversation, "primary"))
        col.addLayout(top)
        split = QHBoxLayout()
        split.setSpacing(14)
        self.sess_list = QListWidget()
        self.sess_list.setFixedWidth(360)
        self.sess_list.setMinimumHeight(520)
        self.sess_list.currentItemChanged.connect(lambda item, _: item and self.preview(item.data(Qt.UserRole)))
        split.addWidget(self.sess_list)
        right, r = card()
        head = QHBoxLayout()
        self.sess_title = label("Pick a conversation", None)
        self.sess_title.setStyleSheet("font-weight: 700; font-size: 11pt;")
        head.addWidget(self.sess_title, 1)
        self.sess_open = button("Continue", self.open_session, "primary")
        self.sess_del = button("Delete", self.delete_session, "danger")
        for b in (self.sess_open, self.sess_del):
            b.setEnabled(False)
            head.addWidget(b)
        r.addLayout(head)
        self.sess_view = QTextBrowser()
        self.sess_view.setOpenExternalLinks(True)
        self.sess_view.document().setDefaultStyleSheet(PREVIEW_CSS)
        r.addWidget(self.sess_view, 1)
        split.addWidget(right, 1)
        col.addLayout(split, 1)
        return page

    def load_sessions(self):
        query = self.sess_search.text().strip()
        def show(d):
            items, current = (d, None) if query else (d["sessions"], d["current"])
            want = self.sess_list.currentItem().data(Qt.UserRole) if self.sess_list.currentItem() else None
            self.sess_list.blockSignals(True)
            self.sess_list.clear()
            for s in items:
                when = time.strftime("%d %b %Y, %H:%M", time.localtime(s["updated"]))
                extra = f"\n“{s['match']}”" if query and s.get("match") and s["match"] != s["title"] else ""
                tag = "   ● now" if s["id"] == current else ""
                item = QListWidgetItem(f"{s['title']}{extra}\n{when} · {s['count']} messages{tag}")
                item.setData(Qt.UserRole, s["id"])
                self.sess_list.addItem(item)
                if s["id"] == want:
                    self.sess_list.setCurrentItem(item)
            if not items:
                self.sess_list.addItem("Nothing found." if query else "No saved conversations yet.")
            self.sess_list.blockSignals(False)
        self.call(f"/api/search?q={quote(query)}" if query else "/api/sessions", then=show)

    def preview(self, sid):
        if not sid:
            return
        def show(s):
            self.selected = sid
            self.sess_title.setText(s["title"])
            self.sess_view.setHtml("".join(message_html(m, self.tool_label) for m in s["messages"]))
            self.sess_open.setEnabled(True)
            self.sess_del.setEnabled(True)
        self.call(f"/api/sessions/{sid}", then=show)

    def open_session(self):
        self.call(f"/api/sessions/{self.selected}/open", {}, lambda _: (self.reload_chat(), self.go("home")))

    def delete_session(self):
        if QMessageBox.question(self, "Delete conversation", "Delete this conversation? This can't be undone.") != QMessageBox.Yes:
            return
        def deleted(_):
            self.sess_view.clear()
            self.sess_title.setText("Pick a conversation")
            self.sess_open.setEnabled(False)
            self.sess_del.setEnabled(False)
            self.load_sessions()
            self.reload_chat()
        self.call(f"/api/sessions/{self.selected}/delete", {}, deleted)

    # ---- activity
    def _activity(self):
        page, col = self.page("Activity", "What Jarvis has done in this conversation")
        grid = QGridLayout()
        grid.setSpacing(12)
        self.tiles = {}
        for i, name in enumerate(["Turns", "Tools run", "Tools available", "Uptime"]):
            tile = QFrame()
            tile.setObjectName("card")
            t = QVBoxLayout(tile)
            t.setContentsMargins(16, 12, 16, 14)
            t.addWidget(label(name.upper(), "cardTitle"))
            self.tiles[name] = label("0", "big")
            t.addWidget(self.tiles[name])
            grid.addWidget(tile, 0, i)
        col.addLayout(grid)
        box, v = card("Tool calls")
        self.activity_empty = label("No tool calls yet in this conversation.", "small")
        v.addWidget(self.activity_empty)
        self.activity = QListWidget()
        self.activity.setMinimumHeight(420)
        self.activity.setFocusPolicy(Qt.NoFocus)
        v.addWidget(self.activity)
        col.addWidget(box)
        return page

    def _activity_row(self, m):
        at = time.strftime("%H:%M:%S", time.localtime(m.get("time", time.time())))
        item = QListWidgetItem(f"{at}    {self.tool_label(m['text'])}    ·    {m['text']}")
        self.activity.insertItem(0, item)

    # ---- accounts
    def _connections(self):
        page, col = self.page("Accounts", "Your accounts, through Composio: connect one and Jarvis can use it right away")
        top = QHBoxLayout()
        self.ws_msg = label("", "small")
        top.addWidget(self.ws_msg, 1)
        top.addWidget(button("↻  Refresh", self.load_connections))
        col.addLayout(top)
        self.ws_grid = QGridLayout()
        self.ws_grid.setSpacing(12)
        col.addLayout(self.ws_grid)
        col.addWidget(label("Built in", "section"))
        built = QGridLayout()
        built.setSpacing(12)
        for i, (ico, name, hint) in enumerate([
                ("Ps", "Photopea", '"Open my latest screenshot in Photopea and crop it square." Jarvis opens files in Photopea and works in it.'),
                ("⌘", "Your PC", "Apps, files, windows, mouse and keyboard, any site in your browser (NotebookLM, WhatsApp Web…).")]):
            built.addWidget(self._ws_card(ico, name, "Ready", True, hint), 0, i)
        col.addLayout(built)
        col.addStretch()
        return page

    def _ws_card(self, ico, name, status, ok, hint=None, action=None):
        frame, c = card()
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top = QHBoxLayout()
        icon = label(ico, None)
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: rgba(63,216,255,.10); color: {CYAN}; border-radius: 12px; font-weight: 700;")
        top.addWidget(icon)
        info = QVBoxLayout()
        info.setSpacing(0)
        title = label(name, None)
        title.setStyleSheet("font-weight: 700;")
        info.addWidget(title)
        info.addWidget(label(f'<span style="color:{GREEN if ok else FAINT}">●</span>&nbsp; {escape(status)}', "small", rich=True))
        top.addLayout(info, 1)
        c.addLayout(top)
        if hint:
            c.addWidget(label(hint, "small", wrap=True))
        if action:
            c.addWidget(action)
        return frame

    def load_connections(self):
        self.ws_msg.setText("Checking your accounts…")
        def show(items):
            if isinstance(items, Exception):
                self.ws_msg.setText(f"Couldn't check accounts: {items}")
                return
            self.ws_msg.setText(f"{sum(w['connected'] for w in items)} connected")
            clear(self.ws_grid)
            for i, w in enumerate(sorted(items, key=lambda w: not w["connected"])):
                b = self._ws_controls(w) if w["connected"] else button("Connect", lambda w=w: self.connect_ws(w), "primary")
                status = (w["account"] or "Connected") if w["connected"] else "Not connected"
                self.ws_grid.addWidget(self._ws_card(w["name"][0], w["name"], status, w["connected"], action=b), i // 3, i % 3)
        run(lambda: self.get("/api/workspaces"), show)

    def _ws_controls(self, w):
        """A connected account's controls: what Jarvis may do with it, reconnect, disconnect (click twice)."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        mode = QComboBox()
        for key, text in ACCOUNT_MODES:
            mode.addItem(text, key)
        mode.setCurrentIndex(max(0, mode.findData(w.get("mode", "ask"))))
        mode.currentIndexChanged.connect(lambda _: self.call(f"/api/workspaces/{w['slug']}/mode", {"mode": mode.currentData()},
                                                             lambda _: self.toast(f"{w['name']}: {mode.currentText()}")))
        lay.addWidget(mode)
        row = QHBoxLayout()
        row.addWidget(button("Reconnect", lambda: self.connect_ws(w)))
        def disconnect():
            if drop.text() == "Disconnect":  # a second click confirms
                drop.setText("Click again to remove")
                QTimer.singleShot(4000, lambda: drop.setText("Disconnect"))
                return
            self.call(f"/api/workspaces/{w['slug']}/disconnect", {}, lambda _: (self.toast(f"{w['name']} disconnected"),
                                                                                self.load_connections()))
        drop = button("Disconnect", disconnect)
        row.addWidget(drop)
        lay.addLayout(row)
        return box

    def connect_ws(self, w):
        self.toast(f"Opening the {w['name']} sign-in…")
        self.call(f"/api/workspaces/{w['slug']}/connect", {},
                  lambda _: self.toast(f"Finish signing in to {w['name']} in your browser, then press Refresh."))

    # ---- plugins
    def _plugins(self):
        page, col = self.page("Plugins", "MCP servers: each one gives Jarvis new tools")
        self.plug_box = QVBoxLayout()
        self.plug_box.setSpacing(10)
        col.addLayout(self.plug_box)
        form, f = card("Add a plugin")
        presets = QGridLayout()
        for i, (text, name, kind, value) in enumerate(PRESETS):
            presets.addWidget(button(f"＋  {text}", lambda n=name, k=kind, val=value: self._preset(n, k, val), "chip"), i // 2, i % 2)
        f.addLayout(presets)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.p_name, self.p_type, self.p_value = QLineEdit(), QComboBox(), QLineEdit()
        self.p_name.setPlaceholderText("notion")
        self.p_type.addItems(["Remote URL", "Local command"])
        self.p_type.currentIndexChanged.connect(self._sync_type)
        self.p_value_label = label("URL", "small")
        grid.addWidget(label("Name", "small"), 0, 0)
        grid.addWidget(label("Type", "small"), 0, 1)
        grid.addWidget(self.p_name, 1, 0)
        grid.addWidget(self.p_type, 1, 1)
        grid.addWidget(self.p_value_label, 2, 0, 1, 2)
        grid.addWidget(self.p_value, 3, 0, 1, 2)
        f.addLayout(grid)
        adv = QWidget()
        a = QVBoxLayout(adv)
        a.setContentsMargins(0, 0, 0, 0)
        self.p_headers, self.p_env, self.p_tools = QPlainTextEdit(), QPlainTextEdit(), QLineEdit()
        for box in (self.p_headers, self.p_env):
            box.setPlaceholderText("{}")
            box.setFixedHeight(64)
        a.addWidget(label('Headers (JSON, for URL plugins), e.g. {"Authorization": "Bearer …"}', "small"))
        a.addWidget(self.p_headers)
        a.addWidget(label("Environment (JSON, for command plugins)", "small"))
        a.addWidget(self.p_env)
        a.addWidget(label("Only these tools (comma-separated; empty = all)", "small"))
        a.addWidget(self.p_tools)
        adv.hide()
        f.addWidget(button("▸  Advanced: headers, environment, tool filter", lambda: adv.setVisible(not adv.isVisible()), "link"))
        f.addWidget(adv)
        row = QHBoxLayout()
        row.addWidget(button("Add plugin", self.add_plugin, "primary"))
        self.p_err = label("", "err", wrap=True)
        row.addWidget(self.p_err, 1)
        f.addLayout(row)
        col.addWidget(form)
        col.addStretch()
        self._sync_type()
        return page

    def _preset(self, name, kind, value):
        self.p_name.setText(name)
        self.p_type.setCurrentIndex(0 if kind == "url" else 1)
        self.p_value.setText(value)

    def _sync_type(self):
        url = self.p_type.currentIndex() == 0
        self.p_value_label.setText("URL" if url else "Command")
        self.p_value.setPlaceholderText("https://mcp.example.com/mcp" if url else "npx -y some-mcp-server --flag")

    def add_plugin(self):
        self.p_err.setText("")
        kind = "url" if self.p_type.currentIndex() == 0 else "command"
        data = {"name": self.p_name.text(), kind: self.p_value.text(), "headers": self.p_headers.toPlainText(),
                "env": self.p_env.toPlainText(), "tools": self.p_tools.text()}
        def done(result):
            if isinstance(result, Exception):
                self.p_err.setText(str(result))
                return
            for box in (self.p_name, self.p_value, self.p_tools, self.p_headers, self.p_env):
                box.clear()
            self.toast("Plugin added. It's connecting now.")
            self.load_plugins()
        run(lambda: self.post("/api/plugins", data), done)

    def load_plugins(self):
        def show(items):
            clear(self.plug_box)
            if not items:
                self.plug_box.addWidget(label("No plugins yet.", "small"))
            for p in items:
                color, status = {"ready": (GREEN, f"ready · {len(p['tools'])} tools"), "connecting": (GOLD, "connecting… (a sign-in may open in your browser)"),
                                 "error": (RED, "error"), "off": (FAINT, "off")}.get(p["status"], (FAINT, p["status"]))
                frame, c = card()
                h = QHBoxLayout()
                info = QVBoxLayout()
                info.addWidget(label(f'<b>{escape(p["name"])}</b>&nbsp;&nbsp; <span style="color:{color}">●</span> '
                                     f'<span style="color:{DIM}">{escape(status)}</span>', rich=True))
                src = label(p["config"].get("url") or p["config"].get("command", ""), "small", wrap=True)
                src.setToolTip(", ".join(p["tools"]))
                info.addWidget(src)
                if p["error"]:
                    info.addWidget(label(p["error"], "err", wrap=True))
                h.addLayout(info, 1)
                h.addWidget(button("Disable" if p["enabled"] else "Enable",
                                   lambda n=p["name"]: self.call(f"/api/plugins/{n}/toggle", {}, lambda _: self.load_plugins())))
                h.addWidget(button("Remove", lambda n=p["name"]: self.remove_plugin(n), "danger"))
                c.addLayout(h)
                self.plug_box.addWidget(frame)
            if any(p["status"] == "connecting" for p in items) and self.current == "plugins":
                QTimer.singleShot(2500, self.load_plugins)
        self.call("/api/plugins", then=show)

    def remove_plugin(self, name):
        extra = " The Accounts page depends on it." if name == "composio" else ""
        if QMessageBox.question(self, "Remove plugin", f"Remove the {name} plugin?{extra}") == QMessageBox.Yes:
            self.call(f"/api/plugins/{name}/delete", {}, lambda _: self.load_plugins())

    # ---- memory and reminders
    def _memory(self):
        page, col = self.page("Memory", 'What Jarvis knows about you, and what it will remind you of')
        box, v = card("What Jarvis remembers")
        v.addWidget(label('Say "remember that…" or edit here, one fact per line. Jarvis reads this at the start of every conversation.',
                          "small", wrap=True))
        self.memory = QPlainTextEdit()
        self.memory.setPlaceholderText("- Prefers short answers")
        self.memory.setMinimumHeight(220)
        v.addWidget(self.memory)
        row = QHBoxLayout()
        row.addWidget(button("Save memory", self.save_memory, "primary"))
        self.mem_result = label("", "small")
        row.addWidget(self.mem_result, 1)
        v.addLayout(row)
        col.addWidget(box)
        rem, self.rem_manage = card("Reminders")
        col.addWidget(rem)
        col.addStretch()
        return page

    def show_reminders_page(self, items):
        clear(self.rem_manage)
        self.rem_manage.addWidget(label("REMINDERS", "cardTitle"))
        if not items:
            self.rem_manage.addWidget(label('Nothing scheduled. Say "remind me at 17:30 to…". Classroom deadlines are added here '
                                            "automatically (Settings).", "small", wrap=True))
        for r in items:
            row = QHBoxLayout()
            when = label(r["when"], None)
            when.setStyleSheet(f"color: {GOLD};")
            when.setFixedWidth(150)
            row.addWidget(when)
            row.addWidget(label(r["text"], wrap=True), 1)
            row.addWidget(button("Cancel", lambda rid=r["id"]: self.call(f"/api/reminders/{rid}/cancel", {}, lambda _: self.load_reminders()), "danger"))
            self.rem_manage.addLayout(row)

    def load_memory(self):
        def show(d):
            if self.memory.document().isModified():  # don't overwrite what's being typed
                return
            self.memory.setPlainText(d["memory"])
            self.memory.document().setModified(False)
        self.call("/api/memory", then=show)

    def save_memory(self):
        def saved(_):
            self.memory.document().setModified(False)
            self.mem_result.setText("Saved.")
            self.load_memory()
        self.call("/api/memory", {"memory": self.memory.toPlainText()}, saved)

    # ---- settings
    def _settings(self):
        page, col = self.page("Settings", "Saved to " + os.path.join(store.CONFIG, "settings.json") + "; voice changes apply from the next conversation")
        self.fields = {"voice": QComboBox(), "live_model": QLineEdit(), "home_city": QLineEdit()}
        self.fields["voice"].setMinimumWidth(220)
        for key, lo, hi, step in (("follow_up_seconds", 0, 120, 1), ("keep_session_seconds", 0, 600, 10), ("end_of_speech_ms", 200, 2000, 50)):
            box = QSpinBox()
            box.setRange(lo, hi)
            box.setSingleStep(step)
            self.fields[key] = box
        wake = QDoubleSpinBox()
        wake.setRange(0.05, 0.99)
        wake.setSingleStep(0.05)
        self.fields["wake_threshold"] = wake
        self.fields["home_city"].setPlaceholderText("e.g. London (empty = detect)")

        def section(title, rows, checks=()):
            box, v = card(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(10)
            for i, (key, text) in enumerate(rows):
                cell = QVBoxLayout()
                cell.setSpacing(4)
                cell.addWidget(label(text, "small", wrap=True))
                cell.addWidget(self.fields[key])
                grid.addLayout(cell, i // 2, i % 2)
            v.addLayout(grid)
            for key, text in checks:
                self.fields[key] = QCheckBox(text)
                v.addWidget(self.fields[key])
            col.addWidget(box)

        section("Voice", [("voice", "Voice"), ("live_model", "Voice model")],
                [("fast_voice", "Fast voice: answer without thinking first (about 0.3 s quicker, less sharp)"),
                 ("speak_typed_replies", "Speak replies to typed messages too")])
        section("Listening", [("follow_up_seconds", "Keep listening after a reply (seconds)"),
                              ("keep_session_seconds", 'Stay connected after a conversation (seconds; makes the next "Hey Jarvis" instant)'),
                              ("end_of_speech_ms", "Pause before Jarvis answers (ms; lower = snappier, higher = fewer cut-offs)"),
                              ("wake_threshold", "Wake word sensitivity (lower = wakes more easily)")],
                [("learn_my_voice", 'Learn my voice: wake-ups you dismiss teach Jarvis what isn\'t you saying "Hey Jarvis"'),
                 ("echo_cancel", "Echo cancelling: talk over Jarvis on speakers (experimental; restart Jarvis to apply)")])
        section("Your day", [("home_city", "Home city for the weather")],
                [("morning_briefing", "Morning briefing: the first time Jarvis starts in a morning, it tells you about your day"),
                 ("deadline_reminders", "Classroom deadlines: reminders a day and two hours before work is due"),
                 ("show_thinking", "Show Jarvis's thinking in the chat (its decisions and the background agent's reasoning)"),
                 ("start_at_login", "Start Jarvis when I log in")])
        box, v = card("Instructions and models")
        for key, text, height in (("extra_instructions", "Your instructions for Jarvis (how to behave, things to know about you)", 90),
                                  ("agent_models", "Background agent models, tried top to bottom: backend model thinking. backend is "
                                                   "aistudio (your API key) or one added in local_backends.py.", 130)):
            v.addWidget(label(text, "small", wrap=True))
            self.fields[key] = QPlainTextEdit()
            self.fields[key].setFixedHeight(height)
            v.addWidget(self.fields[key])
        col.addWidget(box)
        row = QHBoxLayout()
        row.addWidget(button("Save settings", self.save_settings, "primary"))
        self.set_result = label("", "small")
        row.addWidget(self.set_result, 1)
        col.addLayout(row)
        tip, t = card("Push-to-talk")
        t.addWidget(label("System Settings → Keyboard → Shortcuts → Add New → Command or Script: run  jarvis --listen  and bind it to "
                          "e.g. Meta+J. The tray menu's Talk does the same.", "small", wrap=True))
        col.addWidget(tip)
        col.addStretch()
        return page

    def load_settings(self):
        def show(d):
            s = d["settings"]
            self.fields["voice"].clear()
            self.fields["voice"].addItems(list(dict.fromkeys([s["voice"], *d["voices"]])))
            for key, f in self.fields.items():
                value = s[key]
                if isinstance(f, QCheckBox):
                    f.setChecked(bool(value))
                elif isinstance(f, (QSpinBox, QDoubleSpinBox)):
                    f.setValue(value)
                elif isinstance(f, QPlainTextEdit):
                    f.setPlainText("\n".join(value) if isinstance(value, list) else value)
                elif isinstance(f, QLineEdit):
                    f.setText(str(value))
            self.set_result.setText("")
        self.call("/api/settings", then=show)

    def save_settings(self):
        data = {}
        for key, f in self.fields.items():
            if isinstance(f, QCheckBox):
                data[key] = f.isChecked()
            elif isinstance(f, (QSpinBox, QDoubleSpinBox)):
                data[key] = f.value()
            elif isinstance(f, QPlainTextEdit):
                data[key] = f.toPlainText()
            elif isinstance(f, QComboBox):
                data[key] = f.currentText()
            else:
                data[key] = f.text()
        def done(result):
            if isinstance(result, Exception):
                self.set_result.setText(str(result))
                self.set_result.setStyleSheet(f"color: {RED}")
            else:
                self.set_result.setText("Saved.")
                self.set_result.setStyleSheet(f"color: {GREEN}")
                if self.chat.show_thinking != data["show_thinking"]:
                    self.chat.show_thinking = data["show_thinking"]
                    self.reload_chat()
                self.load_today()
        run(lambda: self.post("/api/settings", data), done)
