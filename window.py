"""Jarvis's window: Qt Quick (QML) drawn on the GPU, fed by a small Backend object. The QML calls the app's API through
Backend.request (off the UI thread) and hears everything that happens through Backend.event. The notch stays in jarvis.py."""
import json, os
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Property, QByteArray, QObject, QRectF, Qt, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPainter, QPixmap
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- icons: 24x24 line icons, drawn in any colour
S = '<g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</g>'
F = '<g fill="currentColor" stroke="none">{}</g>'
ICONS = {
    "home": S.format('<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9v11h13V9"/><path d="M10 20v-5.5h4V20"/>'),
    "chats": S.format('<path d="M20.5 11.5a8 8 0 0 1-11.7 7.1L4 20l1.2-4.4A8 8 0 1 1 20.5 11.5z"/><path d="M8.5 10h7M8.5 13.5h4.5"/>'),
    "activity": S.format('<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>'),
    "accounts": S.format('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/>'
                         '<path d="M18.3 14.2A6.5 6.5 0 0 1 21.5 20"/>'),
    "plugins": S.format('<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
                        '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/><path d="M17 13.5v7M13.5 17h7"/>'),
    "memory": S.format('<path d="M12 3.5l2.4 5 5.4.7-4 3.8 1 5.4-4.8-2.6-4.8 2.6 1-5.4-4-3.8 5.4-.7z"/>'),
    "settings": S.format('<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1"/><circle cx="15" cy="7" r="2"/>'
                         '<circle cx="9" cy="12" r="2"/><circle cx="17" cy="17" r="2"/>'),
    "search": S.format('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>'),
    "attach": S.format('<path d="M20.5 11.5l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.6-8.6a3.4 3.4 0 0 1 4.8 4.8L9.8 17.6a1.7 1.7 0 0 1-2.4-2.4l7.7-7.7"/>'),
    "send": S.format('<path d="M12 19V5"/><path d="M5.5 11.5 12 5l6.5 6.5"/>'),
    "pause": F.format('<rect x="6.5" y="5" width="4" height="14" rx="1.2"/><rect x="13.5" y="5" width="4" height="14" rx="1.2"/>'),
    "mic": S.format('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>'),
    "stop": F.format('<rect x="6.5" y="6.5" width="11" height="11" rx="2.5"/>'),
    "play": F.format('<path d="M8 5.5v13a1 1 0 0 0 1.5.9l10-6.5a1 1 0 0 0 0-1.7l-10-6.5A1 1 0 0 0 8 5.5z"/>'),
    "prev": F.format('<path d="M17.5 6v12a.9.9 0 0 1-1.4.7L8 12.8a1 1 0 0 1 0-1.6l8.1-5.9a.9.9 0 0 1 1.4.7z"/><rect x="5" y="5.5" width="2.4" height="13" rx="1"/>'),
    "next": F.format('<path d="M6.5 6v12a.9.9 0 0 0 1.4.7l8.1-5.9a1 1 0 0 0 0-1.6L7.9 5.3a.9.9 0 0 0-1.4.7z"/><rect x="16.6" y="5.5" width="2.4" height="13" rx="1"/>'),
    "plus": S.format('<path d="M12 5v14M5 12h14"/>'),
    "refresh": S.format('<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4.5h-4.5"/>'),
    "close": S.format('<path d="M6 6l12 12M18 6 6 18"/>'),
    "min": S.format('<path d="M6 12h12"/>'),
    "max": S.format('<rect x="5.5" y="5.5" width="13" height="13" rx="2.5"/>'),
    "check": S.format('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    "trash": S.format('<path d="M4.5 7h15M10 4h4M6.5 7l1 13h9l1-13M10 11v5.5M14 11v5.5"/>'),
    "external": S.format('<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>'),
    "key": S.format('<circle cx="8" cy="15" r="4"/><path d="M11 12 20 3M16.5 6.5 19 9M14 9l2 2"/>'),
    "bell": S.format('<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>'),
    "sparkle": S.format('<path d="M12 3c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7z"/><path d="M19 15.5c.2 1.6.9 2.3 2.5 2.5-1.6.2-2.3.9-2.5 2.5-.2-1.6-.9-2.3-2.5-2.5 1.6-.2 2.3-.9 2.5-2.5z"/>'),
    "copy": S.format('<rect x="8.5" y="8.5" width="11" height="11" rx="2.5"/><path d="M15.5 8.5V6A1.5 1.5 0 0 0 14 4.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>'),
    "cpu": S.format('<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>'),
    "sun": S.format('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>'),
    "cloud": S.format('<path d="M7 18.5h10a4 4 0 0 0 .6-8 6 6 0 0 0-11.5 1.5A3.3 3.3 0 0 0 7 18.5z"/>'),
    "bolt": S.format('<path d="M13 2.5 4.5 13.5H12l-1 8 8.5-11H12z"/>'),
    "image": S.format('<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m20.5 16-5-5-8.5 8.5"/>'),
    "mail": S.format('<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m3.5 7 8.5 6 8.5-6"/>'),
    "calendar": S.format('<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
    "screen": S.format('<rect x="3" y="4" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 16.5v4"/>'),
    "timer": S.format('<circle cx="12" cy="13" r="7.5"/><path d="M12 9.5V13l2.5 2M9.5 2.5h5"/>'),
    "music": S.format('<path d="M9 18V5.5l11-2V16"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>'),
    "chevron": S.format('<path d="m6.5 9.5 5.5 5.5 5.5-5.5"/>'),
    "wrench": S.format('<path d="M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3l7.5-7.5"/><path d="M14.5 6.5 17 4a4 4 0 0 1 3 3l-2.5 2.5"/>'),
    "globe": S.format('<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.6 5.4 3.6 8.5s-1.1 5.9-3.6 8.5c-2.5-2.6-3.6-5.4-3.6-8.5s1.1-5.9 3.6-8.5z"/>'),
}


def icon_pixmap(name, color, size):
    """color: a QColor (SVG only knows #rrggbb, so its alpha becomes the icon's opacity)."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g opacity="{color.alphaF():.3f}">'
           f'{ICONS.get(name, ICONS["sparkle"]).replace("currentColor", color.name())}</g></svg>')
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, size, size))
    p.end()
    return pix


class IconProvider(QQuickImageProvider):
    """image://icon/<name>/<rrggbb or aarrggbb>"""

    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)

    def requestPixmap(self, ident, size, requested):
        name, _, color = ident.partition("/")
        px = max(requested.width(), 16) if requested.isValid() else 48
        return icon_pixmap(name, QColor("#" + color), px)




class Backend(QObject):
    reply = Signal(str, str, bool)   # request id, JSON, ok
    event = Signal(str)              # an app event as JSON
    changed = Signal()               # the polled values below
    toastRequested = Signal(str, bool)
    showRequested = Signal()

    def __init__(self, get, post, tool_label, live, shown_state, version):
        super().__init__()
        self.get, self.post, self.label, self.live, self.shown, self.ver = get, post, tool_label, live, shown_state, version
        self.pool = ThreadPoolExecutor(8, thread_name_prefix="ui")
        self._values = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(33)  # ~30 fps: the orb follows your voice
        self.poll()

    def put(self, event):  # (the app's event queues call this: see jarvis.emit)
        self.event.emit(json.dumps(event, ensure_ascii=False, default=str))

    def poll(self):
        values = {"state": self.shown[0], "level": round(getattr(self.live, "level", 0.0), 3), "listening": bool(self.live.mic)}
        if values != self._values:
            self._values = values
            self.changed.emit()

    state = Property(str, lambda self: self._values.get("state", "idle"), notify=changed)
    level = Property(float, lambda self: self._values.get("level", 0.0), notify=changed)
    listening = Property(bool, lambda self: self._values.get("listening", False), notify=changed)

    @Property(str, constant=True)
    def version(self):
        return self.ver

    @Slot(str, str, str)
    def request(self, rid, path, body):
        def work():
            try:
                out = self.get(path) if body == "" else self.post(path, json.loads(body))
                self.reply.emit(rid, json.dumps(out, ensure_ascii=False, default=str), True)
            except KeyError:
                self.reply.emit(rid, json.dumps({"error": "not found"}), False)
            except Exception as e:  # (ValueError: bad input, said as it is)
                self.reply.emit(rid, json.dumps({"error": str(e)[:300]}), False)
        self.pool.submit(work)

    @Slot(str)
    def send(self, text):
        self.request("", "/api/ask", json.dumps({"text": text}))

    @Slot()
    def talk(self):
        self.request("", "/api/listen", "{}")

    @Slot()
    def stop(self):
        self.request("", "/api/stop", "{}")

    @Slot()
    def pause(self):
        self.request("", "/api/pause", "{}")

    @Slot(str)
    def copy(self, text):
        QGuiApplication.clipboard().setText(text)
        self.toast("Copied", False)

    @Slot(str)
    def open(self, target):
        import system
        system.open_target(target)

    @Slot(str, bool)
    def toast(self, text, bad):
        self.toastRequested.emit(text, bad)

    @Slot(str, result=str)
    def toolLabel(self, name):
        return self.label(name)


class Window:
    """The app window: QML on the GPU. Needs a QApplication; QQuickWindow's alpha buffer is set before it's made (jarvis.py)."""

    def __init__(self, get, post, tool_label, live, shown_state, version, show=True):
        current[:] = [self]
        QFontDatabase.addApplicationFont(os.path.join(HERE, "assets", "InterVariable.ttf"))
        QGuiApplication.setFont(QFont("Inter Variable", 10))
        self.backend = Backend(get, post, tool_label, live, shown_state, version)
        self.events = self.backend  # (jarvis.clients takes anything with put())
        qmlRegisterSingletonInstance(Backend, "Jarvis", 1, 0, "Backend", self.backend)
        self.engine = QQmlApplicationEngine()
        self.engine.addImageProvider("icon", IconProvider())
        self.engine.setInitialProperties({"startShown": show})
        self.engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
        if not self.engine.rootObjects():
            raise RuntimeError("the window couldn't be loaded (see the log)")

    def present(self):
        self.backend.showRequested.emit()  # (safe from any thread)


def show():
    """Show the window from any thread (the notch, a second launch, the tray)."""
    if current:
        current[0].present()


current = []  # the one Window
