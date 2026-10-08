"""Line icons for the window (24x24, stroke style), drawn in any colour. Hand-made in the style of Lucide."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

STROKE = '<g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</g>'
FILL = '<g fill="currentColor" stroke="none">{}</g>'
PATHS = {
    "home": STROKE.format('<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9v11h13V9"/><path d="M10 20v-5.5h4V20"/>'),
    "chats": STROKE.format('<path d="M20.5 11.5a8 8 0 0 1-11.7 7.1L4 20l1.2-4.4A8 8 0 1 1 20.5 11.5z"/>'
                           '<path d="M8.5 10h7M8.5 13.5h4.5"/>'),
    "activity": STROKE.format('<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>'),
    "accounts": STROKE.format('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/>'
                              '<path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M18.3 14.2A6.5 6.5 0 0 1 21.5 20"/>'),
    "plugins": STROKE.format('<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
                             '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/><path d="M17 13.5v7M13.5 17h7"/>'),
    "memory": STROKE.format('<path d="M12 3.5l2.4 5 5.4.7-4 3.8 1 5.4-4.8-2.6-4.8 2.6 1-5.4-4-3.8 5.4-.7z"/>'),
    "settings": STROKE.format('<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1"/>'
                              '<circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17" r="2"/>'),
    "search": STROKE.format('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>'),
    "attach": STROKE.format('<path d="M20.5 11.5l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.6-8.6a3.4 3.4 0 0 1 4.8 4.8L9.8 17.6a1.7 1.7 0 0 1-2.4-2.4l7.7-7.7"/>'),
    "send": STROKE.format('<path d="M12 19V5"/><path d="M5.5 11.5 12 5l6.5 6.5"/>'),
    "pause": FILL.format('<rect x="6.5" y="5" width="4" height="14" rx="1.2"/><rect x="13.5" y="5" width="4" height="14" rx="1.2"/>'),
    "mic": STROKE.format('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>'),
    "stop": FILL.format('<rect x="6.5" y="6.5" width="11" height="11" rx="2.5"/>'),
    "play": FILL.format('<path d="M8 5.5v13a1 1 0 0 0 1.5.9l10-6.5a1 1 0 0 0 0-1.7l-10-6.5A1 1 0 0 0 8 5.5z"/>'),
    "prev": FILL.format('<path d="M17.5 6v12a.9.9 0 0 1-1.4.7L8 12.8a1 1 0 0 1 0-1.6l8.1-5.9a.9.9 0 0 1 1.4.7z"/><rect x="5" y="5.5" width="2.4" height="13" rx="1"/>'),
    "next": FILL.format('<path d="M6.5 6v12a.9.9 0 0 0 1.4.7l8.1-5.9a1 1 0 0 0 0-1.6L7.9 5.3a.9.9 0 0 0-1.4.7z"/><rect x="16.6" y="5.5" width="2.4" height="13" rx="1"/>'),
    "plus": STROKE.format('<path d="M12 5v14M5 12h14"/>'),
    "refresh": STROKE.format('<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4.5h-4.5"/>'),
    "close": STROKE.format('<path d="M6 6l12 12M18 6 6 18"/>'),
    "sun": STROKE.format('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>'),
    "bolt": STROKE.format('<path d="M13 2.5 4.5 13.5H12l-1 8 8.5-11H12z"/>'),
    "image": STROKE.format('<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m20.5 16-5-5-8.5 8.5"/>'),
    "mail": STROKE.format('<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m3.5 7 8.5 6 8.5-6"/>'),
    "calendar": STROKE.format('<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'),
    "screen": STROKE.format('<rect x="3" y="4" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 16.5v4"/>'),
    "timer": STROKE.format('<circle cx="12" cy="13" r="7.5"/><path d="M12 9.5V13l2.5 2M9.5 2.5h5"/>'),
}


def svg_icon(name, color, size=24):
    """A crisp icon in the given colour (rendered at twice the size for HiDPI)."""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{PATHS[name].replace("currentColor", color)}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p, QRectF(0, 0, size * 2, size * 2))
    p.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)
