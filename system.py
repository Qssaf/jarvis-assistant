"""Everything that depends on the operating system, behind one small interface: where files live, the microphone and
speaker, screenshots, mouse and keyboard, windows, apps, the shell, notifications, media and starting at login.
Windows and Linux (X11 or Wayland; KDE Plasma gets faster paths). Each function picks the best tool that's installed."""
import json, os, re, shutil, subprocess, sys, tempfile, threading, time

IS_WINDOWS = sys.platform == "win32"
WAYLAND = not IS_WINDOWS and os.environ.get("XDG_SESSION_TYPE") == "wayland"
KDE = "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "")
GNOME = "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "")
HERE = os.path.dirname(os.path.abspath(__file__))
CALC = "calc" if IS_WINDOWS else "kcalc" if KDE else "gnome-calculator"  # for examples in the prompts

# ---------------------------------------------------------------- where things live
if IS_WINDOWS:
    _root = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Jarvis")
    CONFIG, DATA = _root, os.path.join(_root, "data")
else:
    CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "jarvis")
    DATA = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "jarvis")
PICTURES = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis")


def have(program):
    return shutil.which(program) is not None


def run(args, timeout=15, env=None):
    """A short command's output (stdout and stderr), '' if it isn't installed."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (r.stdout + r.stderr).strip()


def describe():
    """A few lines for the models: what this computer is and how to do common things on it."""
    if IS_WINDOWS:
        return ("The computer runs Windows. run_command runs PowerShell (e.g. Get-ChildItem $HOME\\Downloads, Get-Clipboard, "
                "Set-Clipboard 'text'). Open apps with act launch (notepad, calc, explorer, msedge, spotify...); "
                "media keys: act([{keys: \"XF86AudioPlay\"}]).")
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Linux")
    return (f"The computer runs Linux ({desktop}, {'Wayland' if WAYLAND else 'X11'}). run_command runs bash (e.g. ls ~/Downloads; "
            "volume: wpctl set-volume @DEFAULT_AUDIO_SINK@ 50% or pactl; clipboard: wl-paste / xclip). Open apps with act "
            "launch (firefox, dolphin, nautilus, kcalc...); media keys: act([{keys: \"XF86AudioPlay\"}]).")


# ---------------------------------------------------------------- microphone and speaker
def mic_frames(target=None):
    """16 kHz mono int16 frames of 80 ms (1280 samples): PipeWire's pw-record when there (it can use the echo canceller),
    otherwise PortAudio through sounddevice (Windows, PulseAudio/ALSA systems)."""
    import numpy as np
    if not IS_WINDOWS and have("pw-record"):
        p = subprocess.Popen(["pw-record", *(["--target", target] if target else []), "--rate", "16000", "--channels", "1",
                              "--format", "s16", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while chunk := p.stdout.read(2560):
            if len(chunk) == 2560:
                yield np.frombuffer(chunk, np.int16)
        return
    import sounddevice as sd
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1280) as stream:
        while True:
            frames, _ = stream.read(1280)
            yield frames[:, 0].copy()


class AudioOut:
    """A stream of 24 kHz mono 16-bit PCM to the speakers that can be cut off at once: pw-play on PipeWire, else
    sounddevice."""

    def __init__(self, target=None):
        self.target, self.proc, self.stream = target, None, None
        self.pipewire = not IS_WINDOWS and have("pw-play")

    def write(self, pcm):
        if self.pipewire:
            if not self.proc or self.proc.poll() is not None:
                self.proc = subprocess.Popen(["pw-play", *(["--target", self.target] if self.target else []), "--raw", "--rate",
                                              "24000", "--channels", "1", "--format", "s16", "-"],
                                             stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.proc.stdin.write(pcm)
            self.proc.stdin.flush()
        else:
            import numpy as np
            import sounddevice as sd
            if self.stream is None:
                self.stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16")
                self.stream.start()
            self.stream.write(np.frombuffer(pcm, np.int16).tobytes())

    def stop(self):
        if self.proc:
            self.proc.kill()
            try:
                self.proc.stdin.close()
            except OSError:
                pass
            self.proc = None
        if self.stream is not None:
            try:
                self.stream.abort()
                self.stream.close()
            except Exception:
                pass
            self.stream = None


def chime():
    """A short, soft two-note chime (generated, so there's no sound file to ship)."""
    def play():
        import numpy as np
        t = np.linspace(0, 0.09, int(24000 * 0.09), False)
        notes = [np.sin(2 * np.pi * f * t) * np.exp(-t * 30) for f in (880, 1320)]
        tone = (np.concatenate(notes) * 0.25 * 32767).astype(np.int16).tobytes()
        out = AudioOut()
        try:
            out.write(tone)
            time.sleep(0.25)
        finally:
            if out.proc:
                out.proc.stdin.close()
            elif out.stream is not None:
                time.sleep(0.05)
                out.stream.close()
    threading.Thread(target=play, daemon=True).start()


# ---------------------------------------------------------------- screenshots
SHOT_HELPER = os.path.join(DATA, "bin", "jarvis-shot")  # KDE: built by install.sh from jarvis-shot.c


def _jpeg(raw, w, h, stride, fmt):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImage
    out = QByteArray()
    buf = QBuffer(out)
    buf.open(QIODevice.WriteOnly)
    QImage(raw, w, h, stride, fmt).save(buf, "JPG", 85)
    return bytes(out)


def _from_file(args, suffix=".png"):
    path = os.path.join(tempfile.mkdtemp(prefix="jarvis-"), "screen" + suffix)
    run(args + [path] if "{}" not in " ".join(args) else [a.replace("{}", path) for a in args], timeout=20)
    try:
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtGui import QImage
        img = QImage(path)
        if img.isNull():
            return None
        out = QByteArray()
        buf = QBuffer(out)
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "JPG", 85)
        return bytes(out)
    finally:
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def screenshot():
    """A JPEG of the whole screen, by the fastest way this desktop allows."""
    if KDE and WAYLAND and os.path.exists(SHOT_HELPER):  # ~30 ms through KWin
        try:
            raw = subprocess.run([SHOT_HELPER], capture_output=True, timeout=5).stdout
            head, pixels = raw.split(b"\n", 1)
            w, h, stride, fmt = map(int, head.split())
            if w and len(pixels) >= stride * h and pixels.strip(b"\0"):  # (all black: KWin refused this caller)
                from PySide6.QtGui import QImage
                return _jpeg(pixels, w, h, stride, QImage.Format(fmt))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    if WAYLAND:
        if KDE and have("spectacle"):
            return _from_file(["spectacle", "-b", "-n", "-f", "-o"])
        if have("grim"):  # wlroots desktops (Sway, Hyprland...)
            return _from_file(["grim"])
        if GNOME and have("gnome-screenshot"):
            return _from_file(["gnome-screenshot", "-f"])
    import mss  # Windows and X11
    from PySide6.QtGui import QImage
    with mss.mss() as m:
        shot = m.grab(m.monitors[0])
        return _jpeg(bytes(shot.bgra), shot.width, shot.height, shot.width * 4, QImage.Format_ARGB32)


# ---------------------------------------------------------------- mouse and keyboard
WDOTOOL_ENV = dict(os.environ, XDG_STATE_HOME=os.path.join(DATA, "state"), RUST_LOG="error")
_input_lock = threading.Lock()  # one input action at a time (wdotool's permission token is single-use)
KEY_NAMES = {"enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape", "del": "Delete", "delete": "Delete",
             "backspace": "BackSpace", "tab": "Tab", "space": "space", "pageup": "Page_Up", "pgup": "Page_Up", "pagedown": "Page_Down",
             "pgdn": "Page_Down", "home": "Home", "end": "End", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
             "arrowup": "Up", "arrowdown": "Down", "arrowleft": "Left", "arrowright": "Right", "pause": "Pause", "ret": "Return",
             "insert": "Insert", "control": "ctrl", "cmd": "super", "win": "super", "windows": "super", "meta": "super"}


def key_chains(keys):
    """'ctrl+a Enter' -> [['ctrl', 'a'], ['Return']] with common names turned into xkb's."""
    return [[KEY_NAMES.get(k.lower(), k) for k in chain.split("+")] for chain in keys.split()]


def _wayland_tool():
    return "wdotool" if have("wdotool") else "ydotool" if have("ydotool") else None


def _wdo(*args, timeout=15):
    with _input_lock:
        return run(["wdotool", *map(str, args)], timeout=timeout, env=WDOTOOL_ENV)


def _pynput_key(name):
    from pynput.keyboard import Key, KeyCode
    special = {"Return": Key.enter, "Escape": Key.esc, "BackSpace": Key.backspace, "Tab": Key.tab, "space": Key.space,
               "Delete": Key.delete, "Insert": Key.insert, "Home": Key.home, "End": Key.end, "Page_Up": Key.page_up,
               "Page_Down": Key.page_down, "Up": Key.up, "Down": Key.down, "Left": Key.left, "Right": Key.right,
               "ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt, "super": Key.cmd, "Pause": Key.pause,
               "XF86AudioPlay": Key.media_play_pause, "XF86AudioNext": Key.media_next, "XF86AudioPrev": Key.media_previous,
               "XF86AudioMute": Key.media_volume_mute, "XF86AudioRaiseVolume": Key.media_volume_up,
               "XF86AudioLowerVolume": Key.media_volume_down}
    if name in special:
        return special[name]
    if len(name) > 1 and name[0] in "Ff" and name[1:].isdigit():
        return getattr(Key, name.lower())
    if len(name) == 1:
        return KeyCode.from_char(name.lower())
    raise ValueError(f"unknown key '{name}'")


def move_pointer(px, py):
    """'' once the pointer is at (px, py) in screen pixels, else what went wrong."""
    if WAYLAND:
        if _wayland_tool() != "wdotool":
            return "moving the pointer on Wayland needs wdotool"
        for _ in range(3):  # wdotool makes a fresh virtual device per call: the first event is occasionally dropped
            out = _wdo("mousemove", px, py, timeout=40)
            if out:
                return out
            at = _wdo("getmouselocation")
            if at == f"x:{px} y:{py}":
                return ""
        return f"the pointer ended up at {at}"
    from pynput.mouse import Controller
    Controller().position = (px, py)
    return ""


def click(button="left", double=False):
    if WAYLAND:
        tool = _wayland_tool()
        for _ in range(2 if double else 1):
            out = (_wdo("click", {"left": "1", "middle": "2", "right": "3"}[button]) if tool == "wdotool" else
                   run(["ydotool", "click", {"left": "0xC0", "middle": "0xC2", "right": "0xC1"}[button]]) if tool else "no input tool")
            if out and tool != "ydotool":
                return out
        return ""
    from pynput.mouse import Button, Controller
    Controller().click(getattr(Button, button), 2 if double else 1)
    return ""


def type_text(text):
    if WAYLAND:
        tool = _wayland_tool()
        return _wdo("type", text, timeout=60) if tool == "wdotool" else run(["ydotool", "type", text], 60) and "" if tool else \
            "typing on Wayland needs wdotool or ydotool"
    from pynput.keyboard import Controller
    Controller().type(text)
    return ""


def press_keys(keys):
    """Key chains like 'ctrl+l', 'Return', 'ctrl+a BackSpace'; '' when done, else the problem."""
    for chain in key_chains(keys):
        if WAYLAND:
            if _wayland_tool() != "wdotool":
                return "key presses on Wayland need wdotool"
            out = _wdo("key", "+".join(chain), timeout=40)
            if out:
                return out
            continue
        from pynput.keyboard import Controller
        kb, held = Controller(), []
        try:
            for name in chain:
                k = _pynput_key(name)
                kb.press(k)
                held.append(k)
        except ValueError as e:
            return str(e)
        finally:
            for k in reversed(held):
                kb.release(k)
    return ""


def scroll(amount):
    if WAYLAND:
        return _wdo("scroll", 0, int(amount), timeout=40) if _wayland_tool() == "wdotool" else "scrolling on Wayland needs wdotool"
    from pynput.mouse import Controller
    Controller().scroll(0, -int(amount))
    return ""


def screen_size():
    if IS_WINDOWS or not WAYLAND:
        import mss
        with mss.mss() as m:
            return m.monitors[0]["width"], m.monitors[0]["height"]
    return None  # Wayland: taken from the screenshot instead


# ---------------------------------------------------------------- windows
def _kdo(*args):
    return run(["kdotool", *args])


def window_ids():
    if KDE and WAYLAND and have("kdotool"):
        return set(_kdo("search", ".").split())
    if WAYLAND:
        return set()
    import pywinctl
    return {str(w.getHandle()) for w in pywinctl.getAllWindows()}


def active_window():
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("getactivewindow")
    if WAYLAND:
        return ""
    import pywinctl
    w = pywinctl.getActiveWindow()
    return str(w.getHandle()) if w else ""


def active_app():
    """The focused app's name, as the accessibility interface knows it."""
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("getactivewindow", "getwindowclassname").split(".")[-1]
    if WAYLAND:
        return ""
    import pywinctl
    w = pywinctl.getActiveWindow()
    return (w.getAppName() or "").removesuffix(".exe") if w else ""


def list_windows():
    if KDE and WAYLAND and have("kdotool"):
        return [f"{_kdo('getwindowclassname', wid)}: {_kdo('getwindowname', wid)}" for wid in _kdo("search", ".").split()]
    if WAYLAND:
        return ["(listing windows isn't possible on this Wayland desktop; look at the screen instead)"]
    import pywinctl
    return [f"{w.getAppName()}: {w.title}" for w in pywinctl.getAllWindows() if w.title]


def _find_windows(name):
    import pywinctl
    want = name.split(": ", 1)[-1].lower()
    return [w for w in pywinctl.getAllWindows() if want in w.title.lower() or want in (w.getAppName() or "").lower()]


def focus_window(name, wid=None):
    """Bring a window to the front by (part of) its title or app name, or by id."""
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("windowactivate", wid) if wid else _kdo("search", re.escape(name.split(": ", 1)[-1]), "windowactivate")
    if WAYLAND:
        return "switching windows isn't possible on this Wayland desktop; use keyboard shortcuts (alt+tab)"
    import pywinctl
    found = [w for w in pywinctl.getAllWindows() if str(w.getHandle()) == wid] if wid else _find_windows(name)
    if not found:
        return f"no window matching {name}"
    found[0].activate()
    return ""


def close_window(name):
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("search", re.escape(name.split(": ", 1)[-1]), "windowclose")
    if WAYLAND:
        return "closing windows by name isn't possible on this Wayland desktop; use alt+F4 on the focused window"
    found = _find_windows(name)
    if not found:
        return f"no window matching {name}"
    for w in found:
        w.close()
    return ""


# ---------------------------------------------------------------- apps, links, the shell
def program_exists(command):
    """Whether a launch command's program can be found (Windows resolves more names itself, so it's always tried)."""
    words = [w for w in command.split() if w not in ("setsid", "-f", "nohup", "env", "exec") and "=" not in w]
    return IS_WINDOWS or not words or have(os.path.expanduser(words[0]))


def launch(command, env=None):
    """Start an app without waiting for it."""
    if IS_WINDOWS:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(f'start "" {command}', shell=True, creationflags=flags, env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["bash", "-lc", command], start_new_session=True, env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_target(target):
    """Open a web address or file with the default app."""
    if IS_WINDOWS:
        os.startfile(target)
    else:
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def shell(command, timeout=30):
    """Run a command (bash, or PowerShell on Windows); (exit code, output). Output goes to a file, not a pipe, so an app
    started in the background can't keep the call waiting."""
    args = (["powershell", "-NoProfile", "-NonInteractive", "-Command", command] if IS_WINDOWS else ["bash", "-lc", command])
    with tempfile.TemporaryFile() as log:
        r = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=timeout,
                           **({} if IS_WINDOWS else {"start_new_session": True}))
        log.seek(0)
        return r.returncode, log.read().decode(errors="replace").strip()


def similar_programs(name):
    """Installed programs and app-menu entries whose name contains name's first part ("brave-browser" -> brave...)."""
    want, found = os.path.basename(name).lower().split("-")[0], set()
    for d in dict.fromkeys(os.environ.get("PATH", "").split(os.pathsep)):
        if os.path.isdir(d):
            found |= {f for f in os.listdir(d) if want in f.lower()}
    entries = set()
    for apps in ("/usr/share/applications", os.path.expanduser("~/.local/share/applications")):
        if os.path.isdir(apps):
            entries |= {f"gtk-launch {f[:-8]}" for f in os.listdir(apps) if f.endswith(".desktop") and want in f.lower()}
    return (sorted(found, key=len) + sorted(entries, key=len))[:12]


CHROMIUM_BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "brave", "msedge", "chrome")


def chromium_based(program):
    """Whether a program is a Chromium browser or an Electron app (Discord, VS Code, Spotify...), following launcher
    scripts to what they start. On Linux those only show their controls to accessibility tools when started with
    --force-renderer-accessibility (Windows' UI Automation needs nothing)."""
    path = shutil.which(os.path.expanduser(program))
    if IS_WINDOWS or not path:
        return False
    if os.path.basename(path) in CHROMIUM_BROWSERS:
        return True
    for _ in range(3):  # e.g. a /usr/bin script that runs /usr/lib/app/app, which sits next to Chromium's resources.pak
        path = os.path.realpath(path)
        if os.path.exists(os.path.join(os.path.dirname(path), "resources.pak")):
            return True
        try:
            with open(path, "rb") as f:
                script = f.read(65536)
        except OSError:
            return False
        if not script.startswith(b"#!"):
            return False
        body = script.decode(errors="ignore").split("\n", 1)[-1]  # (not the #! line's interpreter)
        if re.search(r"(?i)\belectron", body):  # runs the system's Electron, or says it's one
            return True
        path = next((p for p in re.findall(r"(?<![\w$}])/[\w.+/-]+", body) if os.path.isfile(p) and os.access(p, os.X_OK)), None)
        if not path:
            return False
    return False


def headless_browser():
    """A Chromium-family browser for rendering JavaScript-heavy pages, or None."""
    for name in CHROMIUM_BROWSERS:
        if have(name):
            return shutil.which(name)
    if IS_WINDOWS:
        for path in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
            if os.path.exists(path):
                return path
    return None


# ---------------------------------------------------------------- notifications, media, stats, login
notifier = [None]  # set by the tray app: shows a balloon from the tray icon


def notify(title, text):
    if not IS_WINDOWS and have("notify-send"):
        subprocess.Popen(["notify-send", "-a", "Jarvis", "-i", os.path.join(HERE, "icon.svg"), title, text], stderr=subprocess.DEVNULL)
    elif notifier[0]:
        notifier[0](title, text)


def now_playing():
    """The media player that's playing (or the first one): {player, app, status, title, artist, art}. Linux (MPRIS) only."""
    if IS_WINDOWS or not have("busctl"):
        return {}
    out = run(["busctl", "--user", "--json=short", "call", "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "ListNames"], 5)
    try:
        players = [n for n in json.loads(out)["data"][0] if n.startswith("org.mpris.MediaPlayer2.")]
    except (ValueError, KeyError, IndexError):
        return {}
    best = {}
    for name in players:
        def prop(p):
            try:
                return json.loads(run(["busctl", "--user", "--json=short", "get-property", name, "/org/mpris/MediaPlayer2",
                                       "org.mpris.MediaPlayer2.Player", p], 5))["data"]
            except ValueError:
                return None
        status, meta = prop("PlaybackStatus"), prop("Metadata") or {}
        get = lambda k: (meta.get(k) or {}).get("data")
        info = {"player": name, "app": name.split(".")[-1].split("_")[0].title(), "status": status, "title": get("xesam:title") or "",
                "artist": ", ".join(get("xesam:artist") or []), "art": get("mpris:artUrl") or "",
                "length": (get("mpris:length") or 0) / 1e6}
        if not best or status == "Playing":
            best = info
        if status == "Playing":
            break
    return best


def media(action):
    """PlayPause, Next or Previous for the current player (media keys where MPRIS isn't available)."""
    player = now_playing().get("player")
    if player:
        run(["busctl", "--user", "call", player, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", action], 5)
    else:
        press_keys({"PlayPause": "XF86AudioPlay", "Next": "XF86AudioNext", "Previous": "XF86AudioPrev"}[action])


def system_stats():
    import psutil
    mem, disk = psutil.virtual_memory(), psutil.disk_usage(os.path.expanduser("~"))
    return {"cpu": round(psutil.cpu_percent(interval=None), 1), "mem_used": mem.total - mem.available, "mem_total": mem.total,
            "disk_used": disk.used, "disk_total": disk.total, "uptime": time.time() - psutil.boot_time()}


def set_autostart(enabled, command):
    """Start Jarvis at login: a .desktop file in ~/.config/autostart, or a shortcut script in the Windows Startup folder."""
    if IS_WINDOWS:
        path = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup", "Jarvis.bat")
        body = f'@echo off\r\nstart "" {command}\r\n'
    else:
        path = os.path.expanduser("~/.config/autostart/jarvis.desktop")
        body = (f"[Desktop Entry]\nType=Application\nName=Jarvis\nExec={command}\nIcon={os.path.join(HERE, 'icon.svg')}\n"
                "X-KDE-autostart-phase=2\nTerminal=false\n")
    if enabled:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(body)
    elif os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------- pressing app controls by name (accessibility)
class LinuxAccessibility:
    """AT-SPI through atspi_helper.py, which runs under the system Python (it needs the gi bindings)."""

    def __init__(self):
        self.proc, self.lock = None, threading.Lock()

    def ask(self, cmd, timeout=20):
        import select
        python = "/usr/bin/python3"
        if not os.path.exists(python):
            return {"error": "pressing controls by name needs the system Python with gi (python-gobject) for AT-SPI"}
        with self.lock:
            if not self.proc or self.proc.poll() is not None:
                self.proc = subprocess.Popen([python, os.path.join(HERE, "atspi_helper.py")], text=True,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.proc.stdin.write(json.dumps(cmd) + "\n")
            self.proc.stdin.flush()
            if not select.select([self.proc.stdout], [], [], timeout)[0]:
                self.proc.kill()  # stuck on an unresponsive app: start fresh next time
                return {"error": "the app didn't answer the accessibility request"}
            return json.loads(self.proc.stdout.readline() or '{"error": "accessibility helper exited"}')


class WindowsAccessibility:
    """UI Automation through pywinauto: the same commands as the Linux helper (controls, press, set_text)."""

    INTERACTIVE = {"Button", "CheckBox", "RadioButton", "MenuItem", "Edit", "ComboBox", "Hyperlink", "ListItem", "TabItem",
                   "TreeItem", "Spinner", "Slider", "Document", "SplitButton"}

    def ask(self, cmd, timeout=20):
        try:
            from pywinauto import Desktop
        except ImportError:
            return {"error": "pressing controls by name needs pywinauto (pip install pywinauto)"}
        want = cmd["app"].lower().removesuffix(".exe").split(".")[-1]
        end = time.time() + float(cmd.get("wait", 0))
        while True:
            wins = [w for w in Desktop(backend="uia").windows() if want in (w.window_text() or "").lower()
                    or want in (getattr(w.element_info, "name", "") or "").lower()
                    or want in _process_name(w.element_info.process_id)]
            if wins or time.time() >= end:
                break
            time.sleep(0.2)
        if not wins:
            return {"error": f"no window for '{cmd['app']}'"}
        controls = [c for c in wins[0].descendants() if c.element_info.control_type in self.INTERACTIVE and c.window_text()]
        names = [f"{c.element_info.control_type}: {c.window_text()}" for c in controls]

        def lookup(name):
            low = name.lower().strip()
            return next((c for c in controls if c.window_text().lower() == low), None) or \
                next((c for c in controls if low in c.window_text().lower()), None)
        if cmd["cmd"] == "controls":
            return {"app": wins[0].window_text(), "controls": names[:400]}
        if cmd["cmd"] == "press":
            pressed = []
            for name in cmd["names"]:
                c = lookup(name)
                if c is None:
                    return {"error": f"no control named '{name}'", "pressed": pressed, "available": names[:200]}
                try:
                    c.invoke()
                except Exception:
                    c.click_input()
                pressed.append(name)
                time.sleep(0.1)
            return {"pressed": pressed}
        if cmd["cmd"] == "set_text":
            c = lookup(cmd["field"]) if cmd.get("field") else next((x for x in controls if x.element_info.control_type == "Edit"), None)
            if c is None:
                return {"error": f"no text field '{cmd.get('field', '')}'", "available": names[:200]}
            c.set_edit_text(cmd["text"])
            return {"set": cmd.get("field") or "first text field"}
        return {"error": f"unknown command {cmd['cmd']}"}


def _process_name(pid):
    try:
        import psutil
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


accessibility = WindowsAccessibility() if IS_WINDOWS else LinuxAccessibility()
