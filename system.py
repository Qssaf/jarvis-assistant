"""Everything that depends on the operating system, behind one small interface: where files live, the microphone and
speaker, screenshots, mouse and keyboard, windows, apps, the shell, notifications, media and starting at login.
Windows and Linux (X11 or Wayland; KDE Plasma gets faster paths). Each function picks the best tool that's installed."""
import atexit, functools, json, os, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time

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
# QHealth (the user's screen-time app) keeps its data here, by its own paths.py (not XDG_DATA_HOME); Jarvis only reads it
QHEALTH_DB = (os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local"), "QHealth", "qhealth.db")
              if IS_WINDOWS else os.path.expanduser("~/.local/share/qhealth/qhealth.db"))


def have(program):
    return shutil.which(program) is not None


def app_config(app):
    """Another app's own settings folder (OpenChamber's: the port its local server listens on)."""
    return os.path.join(os.environ.get("APPDATA", "") if IS_WINDOWS else os.environ.get("XDG_CONFIG_HOME") or
                        os.path.expanduser("~/.config"), app)


def lean_memory():
    """glibc gives each thread that allocates its own arena (up to 8 per core) and keeps what's freed in it: Jarvis has
    ~60 threads, mostly asleep, so freed memory piled up in dozens of them. Two shared arenas, set before the threads
    start, hold far less for the same speed on light threads."""
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").mallopt(-8, 2)  # M_ARENA_MAX
        except (OSError, AttributeError):
            pass


def trim_memory():
    """Hand memory freed after a one-off peak (loading models) back to the OS: glibc keeps it for the process otherwise.
    Also drops the source lines Python keeps of every file a logged error's traceback went through (~10 MB after a day)."""
    import linecache
    linecache.clearcache()
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except (OSError, AttributeError):  # (musl has no malloc_trim)
            pass


def run(args, timeout=15, env=None, strip=True):
    """A short command's output (stdout and stderr), '' if it isn't installed. strip: without the blank lines around it."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=timeout, env=env,  # (a copied picture isn't UTF-8)
                           creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0)  # (Jarvis.exe has no console: no window pops up)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (r.stdout + r.stderr).strip() if strip else r.stdout + r.stderr


def _kill_tree(proc):
    """Stop a process started in its own session, with everything it started (npx runs wrangler, which keeps the output
    open; a shell's pipeline)."""
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(proc.pid, 9)
        except OSError:
            pass


def run_lines(args, on_line, cwd=None, timeout=600, halt=None, stdin_text=None):
    """A long command (npx on Windows is npx.cmd: it's found on PATH), each line it prints passed to on_line as it comes.
    Only stdin_text is typed to it (free text goes there, never in args: a .cmd's arguments go through cmd.exe, which
    splits them at quotes, & or a new line), and it's stopped after timeout seconds, or when halt (an Event) is set.
    Its exit code."""
    proc = subprocess.Popen([shutil.which(args[0]) or args[0], *args[1:]], cwd=cwd,
                            stdin=subprocess.DEVNULL if stdin_text is None else subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0, start_new_session=not IS_WINDOWS)

    stop = lambda: _kill_tree(proc)
    done, end = threading.Event(), time.time() + timeout

    def watch():
        while not done.wait(0.5):
            if time.time() > end or halt and halt.is_set():
                return stop()
    threading.Thread(target=watch, daemon=True).start()
    if stdin_text is not None:
        def feed():  # (its own thread: a big text mustn't block reading what it prints)
            try:
                with proc.stdin:
                    proc.stdin.write(stdin_text)
            except OSError:  # (it ended without reading it all)
                pass
        threading.Thread(target=feed, daemon=True).start()
    try:
        for line in proc.stdout:
            on_line(line.rstrip())
        return proc.wait()
    finally:
        done.set()


def describe():
    """A few lines for the models: what this computer is and how to do common things on it."""
    # (the home folder said outright: a model guessed /home/<user name>, and the two differed)
    home = f"The user's home folder is {os.path.expanduser('~')}. "
    # (asked how much memory it uses, the voice said it "runs remotely": it's a program here, and can measure itself)
    mine = (f" Jarvis itself is a program on this PC (process {os.getpid()}): its own memory or CPU use is measured with run_command "
            + (f"(Get-Process -Id {os.getpid()})" if IS_WINDOWS else f"(ps -o rss=,pcpu= -p {os.getpid()})") + ", never guessed.")
    if IS_WINDOWS:
        return (home + "The computer runs Windows. run_command runs PowerShell (e.g. Get-ChildItem $HOME\\Downloads, Get-Clipboard, "
                "Set-Clipboard 'text'). Open apps with act launch (notepad, calc, explorer, msedge, spotify...); "
                "media keys: act([{keys: \"XF86AudioPlay\"}])." + mine)
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Linux")
    return (home + f"The computer runs Linux ({desktop}, {'Wayland' if WAYLAND else 'X11'}). run_command runs bash (e.g. ls ~/Downloads; "
            "volume: wpctl set-volume @DEFAULT_AUDIO_SINK@ 50% or pactl; clipboard: wl-paste / xclip). Open apps with act "
            "launch (firefox, dolphin, nautilus, kcalc...); media keys: act([{keys: \"XF86AudioPlay\"}])." + mine)


PROJECT_DEPTH = 3  # folders below home a project may sit ("~/Desktop/Code/game")
PROJECT_SKIP = {"node_modules", "venv", "site-packages", "vendor", "build", "dist", "target", "snap", "go", "AppData", "Library"}
PROJECT_LOOKS = 3000  # folders looked at, at most (a home folder with a huge tree isn't walked)
_projects = {}  # home -> (when looked, the list): asked for with every prompt, looked for every ten minutes


def projects(home=None, limit=20):
    """The user's git projects as "~/Projects/name", the one worked in last first: the models' map of where code lives
    (asked to work "on jarvis", the voice made up ~/jarvis). Nothing hidden, nothing inside another project, and never
    more than PROJECT_LOOKS folders looked at."""
    home = os.path.realpath(home or os.path.expanduser("~"))
    at, found = _projects.get(home, (0, []))
    if time.time() - at < 600:
        return found[:limit]
    found, level, seen = [], [home], 0
    for _ in range(PROJECT_DEPTH):
        deeper = []
        for folder in level:
            try:
                entries = [e for e in os.scandir(folder) if not e.name.startswith(".") and e.name not in PROJECT_SKIP
                           and e.is_dir(follow_symlinks=False)]
            except OSError:  # (one it may not read: the others are still looked at)
                continue
            for e in entries[:max(0, PROJECT_LOOKS - seen)]:
                seen += 1
                git = os.path.join(e.path, ".git")
                if os.path.exists(git):
                    found.append((os.path.getmtime(git), "~/" + os.path.relpath(e.path, home).replace(os.sep, "/")))
                else:
                    deeper.append(e.path)
        level = deeper if seen < PROJECT_LOOKS else []
    found = [name for _, name in sorted(found, reverse=True)]
    _projects[home] = (time.time(), found)
    return found[:limit]


# ---------------------------------------------------------------- microphone and speaker
def mic_frames(target=None, on_source=None):
    """16 kHz mono int16 frames of 80 ms (1280 samples): PipeWire's pw-record when there (it can use the echo canceller),
    otherwise PortAudio through sounddevice (Windows, PulseAudio/ALSA systems). on_source gets the name of the node
    pw-record really reads, a few seconds after each start. On Windows any target means the echo canceller below,
    and on_source hears about it only if that can't start (then it's the plain mic)."""
    import numpy as np
    if IS_WINDOWS and target:
        while True:
            started = time.time()
            try:
                yield from _echo_cancelled_mic()
                print("[voice] the speakers changed: starting echo cancelling again", flush=True)
            except Exception as e:
                if time.time() - started < 10:
                    print(f"[voice] echo cancelling couldn't start: {e}", flush=True)
                    if on_source:
                        on_source("the plain microphone")
                    break
                print(f"[voice] echo cancelling stopped ({e}): starting it again", flush=True)
                time.sleep(1)
    elif not IS_WINDOWS and have("pw-record"):
        while True:  # pw-record quits when PipeWire restarts (an update, a new device): start it again, or Jarvis goes deaf
            # dont-move: otherwise WirePlumber's "follow the default mic" (target.node -1 in its metadata) moves the stream
            # off the echo canceller onto the raw mic, and Jarvis hears its own voice with nothing taken out
            pin = ["--target", target, "-P", "{ node.dont-move = true }"] if target else []
            # --raw: to a pipe pw-record otherwise writes an .au stream, big-endian since PipeWire 1.6.10. Read as ours,
            # quiet sound came through and anything loud enough for a call was noise: Jarvis went deaf as the mic went up
            p = subprocess.Popen(["pw-record", *pin, "--raw", "--rate", "16000", "--channels", "1",
                                  "--format", "s16", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if on_source:
                threading.Timer(3, lambda pid=p.pid: on_source(mic_source(pid))).start()
            started = time.time()
            while chunk := p.stdout.read(2560):
                if len(chunk) == 2560:
                    yield np.frombuffer(chunk, np.int16)
            print(f"[voice] the microphone stream stopped (pw-record exit {p.wait()}): starting it again", flush=True)
            time.sleep(1 if time.time() - started > 10 else 10)  # (failing at once: wait longer, don't spin)
    import sounddevice as sd
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1280) as stream:
        while True:
            frames, _ = stream.read(1280)
            yield frames[:, 0].copy()


def _echo_cancelled_mic():
    """Windows: the default mic with whatever the default speakers play (Jarvis, games, videos, calls) taken out, as
    PipeWire's echo canceller does on Linux: the same WebRTC canceller (from livekit), fed a WASAPI loopback of the
    speakers (soundcard). 80 ms frames like mic_frames; it ends when the default speakers change."""
    import collections, ctypes, itertools
    import numpy as np
    import soundcard
    from livekit import rtc
    if IS_WINDOWS:
        ctypes.windll.ole32.CoInitializeEx(None, 0)  # (soundcard's COM calls need it on each thread)
    pcm = lambda block: bytearray((np.clip(block[:, 0], -1, 1) * 32767).astype(np.int16).tobytes())
    speaker = soundcard.default_speaker()
    loopback = soundcard.get_microphone(speaker.id, include_loopback=True)
    apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True, high_pass_filter=True)
    played, done, why = collections.deque(maxlen=50), threading.Event(), []  # 10 ms frames the speakers played (0.5 s at most)

    def listen_to_speakers():
        if IS_WINDOWS:
            ctypes.windll.ole32.CoInitializeEx(None, 0)
        try:
            with loopback.recorder(16000, channels=1, blocksize=8000) as r:  # (silence comes in as zeros: soundcard fills the gaps)
                while not done.is_set():
                    played.append(pcm(r.record(160)))
        except Exception as e:
            why.append(e)
        done.set()
    threading.Thread(target=listen_to_speakers, daemon=True).start()
    try:
        # half a second of room in WASAPI's buffers (soundcard's default is one 10 ms period): a slower moment in
        # voice_loop would otherwise drop mic sound, and the canceller would lose its place against the speakers
        with soundcard.default_microphone().recorder(16000, channels=1, blocksize=8000) as mic:
            out = []
            for i in itertools.count():
                if done.is_set():
                    raise RuntimeError(f"the speakers' sound stopped coming in ({why[0] if why else 'closed'})")
                if i % 300 == 299 and soundcard.default_speaker().id != speaker.id:
                    return
                while played:  # what was played goes in first: the canceller looks for it in the mic afterwards
                    apm.process_reverse_stream(rtc.AudioFrame(played.popleft(), 16000, 1, 160))
                frame = rtc.AudioFrame(pcm(mic.record(160)), 16000, 1, 160)
                apm.process_stream(frame)  # (in place)
                out.append(np.frombuffer(frame.data, np.int16).copy())
                if len(out) == 8:
                    yield np.concatenate(out)
                    out = []
    finally:
        done.set()


def mic_source(pid):
    """The name of the node a pw-record process really reads ('' if unknown), whatever it asked for."""
    try:
        objects = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=5).stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return ""
    props = lambda kind: {o["id"]: (o.get("info") or {}).get("props") or {} for o in objects if o.get("type", "").endswith(kind)}
    nodes, clients = props(":Node"), props(":Client")
    mine = {i for i, p in nodes.items() if str(clients.get(p.get("client.id"), {}).get("application.process.id")) == str(pid)}
    for o in objects:
        link = o.get("info") or {}
        if o.get("type", "").endswith(":Link") and link.get("input-node-id") in mine:
            return nodes.get(link.get("output-node-id"), {}).get("node.name", "")
    return ""


class AudioOut:
    """A stream of 24 kHz mono 16-bit PCM to the speakers that can be cut off at once: pw-play on PipeWire, else
    sounddevice."""

    def __init__(self, target=None):
        self.target, self.proc, self.stream = target, None, None
        self.pipewire = not IS_WINDOWS and have("pw-play")

    def write(self, pcm):
        if self.pipewire:
            proc = self.proc  # (stop() may clear it from another thread meanwhile)
            if not proc or proc.poll() is not None:
                proc = self.proc = subprocess.Popen(["pw-play", *(["--target", self.target] if self.target else []), "--raw", "--rate",
                                                     "24000", "--channels", "1", "--format", "s16", "-"],
                                                    stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            proc.stdin.write(pcm)
            proc.stdin.flush()
        else:
            import numpy as np
            import sounddevice as sd
            if self.stream is None:
                self.stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16")
                self.stream.start()
            self.stream.write(np.frombuffer(pcm, np.int16).tobytes())

    def stop(self):
        proc, self.proc = self.proc, None  # the speaker thread and the Stop button can both get here at once
        if proc:
            proc.kill()
            try:
                proc.stdin.close()
            except OSError:
                pass
        if self.stream is not None:
            try:
                self.stream.abort()
                self.stream.close()
            except Exception:
                pass
            self.stream = None


def record_audio(path, source="pc"):
    """Start recording to a 16 kHz mono WAV: what the PC is playing ("pc"), the microphone ("room"), or both at once
    ("both": mixed into path when stopped). The process (both: a dict); end it with stop_recording, which finishes the file."""
    if IS_WINDOWS or not have("pw-record"):
        raise RuntimeError("recording needs PipeWire (Linux)")
    if source == "both":
        return {"path": path, "parts": [record_audio(path + ".pc.wav", "pc"), record_audio(path + ".mic.wav", "room")]}
    what = ["-P", "{ stream.capture.sink=true }"] if source == "pc" else []
    limit = ["timeout", "-s", "INT", str(RECORD_LIMIT)] if have("timeout") else []
    proc = subprocess.Popen([*limit, "pw-record", *what, "--rate", "16000", "--channels", "1", "--format", "s16", path],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _recording.add(proc)
    return proc


# a recorder writes to a file, so nothing ended it when Jarvis quit, restarted or crashed while notes were on: one went on
# recording the PC's sound for a day. Each now ends by itself (notes cut a piece every 5 minutes), and all end with Jarvis
RECORD_LIMIT = 600
_recording = set()


@atexit.register
def end_recordings():
    import signal
    for proc in list(_recording):
        _recording.discard(proc)
        try:
            proc.send_signal(signal.SIGINT)
        except OSError:
            pass


def mix_wavs(paths, out):
    """16 kHz mono 16-bit WAVs added together into out (as long as the longest; loud parts clip rather than wrap). The
    parts are removed; one that didn't record leaves the other."""
    import wave
    import numpy as np
    tracks = []
    for p in paths:
        try:
            with wave.open(p) as w:
                tracks.append(np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.int32))
        except (OSError, EOFError, wave.Error):
            pass
        finally:
            if os.path.exists(p):
                os.remove(p)
    mixed = np.zeros(max((len(t) for t in tracks), default=0), np.int32)
    for t in tracks:
        mixed[:len(t)] += t
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(np.clip(mixed, -32768, 32767).astype(np.int16).tobytes())


def audio_chunks(path, folder, seconds=300):
    """A recording (any format: a voice recorder's, a call's) cut by ffmpeg into 16 kHz mono WAV files of `seconds` each,
    in order, in folder."""
    if not have("ffmpeg"):
        raise RuntimeError("reading a recording needs ffmpeg installed (Linux: the package manager; Windows: winget install ffmpeg)")
    said = run(["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-ac", "1", "-ar", "16000", "-f", "segment", "-segment_time",
                str(seconds), os.path.join(folder, "%03d.wav")], timeout=600)
    chunks = sorted(os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".wav"))
    if not chunks:
        raise RuntimeError(f"ffmpeg couldn't read that recording: {said[:200]}")
    return chunks


def stop_recording(proc):
    import signal
    if isinstance(proc, dict):  # (both: each side stopped, then mixed into one file)
        for part in proc["parts"]:
            stop_recording(part)
        return mix_wavs([proc["path"] + ".pc.wav", proc["path"] + ".mic.wav"], proc["path"])
    _recording.discard(proc)
    proc.send_signal(signal.SIGINT)  # (pw-record finishes the WAV header on SIGINT; timeout passes it on)
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()


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


def own_voice():
    """The computer's own text-to-speech ('' if none): SAPI on Windows, espeak-ng or espeak on Linux."""
    return "SAPI" if IS_WINDOWS else next((p for p in ("espeak-ng", "espeak") if have(p)), "")


def speech_wav(text):
    """text said in the computer's own voice, as a WAV: the backup voice's last resort (nothing to download). None
    without one."""
    voice = own_voice()
    if voice == "SAPI":
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:  # (the text goes in through the environment, never into the command)
            run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Speech; $s = New-Object "
                 "System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile($env:JARVIS_WAV); $s.Speak($env:JARVIS_SAY); "
                 "$s.Dispose()"], 60, env=dict(os.environ, JARVIS_WAV=path, JARVIS_SAY=text))
            with open(path, "rb") as f:
                return f.read() or None
        finally:
            os.remove(path)
    if voice:
        return subprocess.run([voice, "--stdout", "--stdin"], input=text.encode(), capture_output=True, timeout=60).stdout or None
    return None


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


def small_jpeg(data, width=1280, quality=60):
    """A JPEG scaled down to at most this wide (the phone app's look at the screen: ~150 KB instead of 1 MB)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QImage
    img = QImage.fromData(data)
    if img.isNull():
        return data
    if img.width() > width:
        img = img.scaledToWidth(width, Qt.SmoothTransformation)
    out = QByteArray()
    buf = QBuffer(out)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "JPG", quality)
    return bytes(out)


def local_addresses():
    """This PC's IPv4 addresses a phone could reach (Wi-Fi, Ethernet, a VPN like Tailscale), the default route's first:
    not loopback, link-local, or the bridges of containers and virtual machines."""
    import psutil
    import socket
    up = {name for name, s in psutil.net_if_stats().items() if s.isup}
    found = [a.address for name, addrs in psutil.net_if_addrs().items()
             if name in up and not name.lower().startswith(("docker", "br-", "veth", "virbr", "vmnet", "vethernet"))
             for a in addrs if a.family == socket.AF_INET and not a.address.startswith(("127.", "169.254."))]
    main = ""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # (nothing is sent: it only asks which address would be used)
            main = s.getsockname()[0]
    except OSError:
        pass
    return sorted(dict.fromkeys(found), key=lambda a: a != main)[:4]


def _from_file(args, suffix=".png", timeout=10):
    path = os.path.join(tempfile.mkdtemp(prefix="jarvis-"), "screen" + suffix)
    run(args + [path] if "{}" not in " ".join(args) else [a.replace("{}", path) for a in args], timeout=timeout)
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
    shot = _screenshot()
    if not shot:
        raise RuntimeError("couldn't take a screenshot: no screenshot tool on this desktop answered")
    return shot


def _screenshot():
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


def capture_region():
    """Let the user drag over part of the screen; that part as a JPEG, or None if they cancelled (or nothing here can)."""
    if WAYLAND and KDE and have("spectacle"):
        return _from_file(["spectacle", "-b", "-n", "-r", "-o"], timeout=120)
    if WAYLAND and have("grim") and have("slurp"):
        area = run(["slurp"], 120)
        return _from_file(["grim", "-g", area]) if re.fullmatch(r"\d+,\d+ \d+x\d+", area) else None
    if not WAYLAND and not IS_WINDOWS and have("maim"):
        return _from_file(["maim", "-s"], timeout=120)
    return None


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


PERMISSION_PENDING = ("timed out: the desktop is still waiting for the user to allow Jarvis's input control in its permission "
                      "prompt (Remote Control)")
_input_blocked_until = [0.0]  # after a timed-out permission prompt, fail fast for a minute instead of waiting again


def _wdo(*args, timeout=15):
    if time.time() < _input_blocked_until[0]:
        return PERMISSION_PENDING
    with _input_lock:
        try:
            r = subprocess.run(["wdotool", *map(str, args)], capture_output=True, text=True, timeout=timeout, env=WDOTOOL_ENV)
            if r.returncode != 0 and "no keyboard device from EIS" in (r.stderr or ""):
                r = subprocess.run(["wdotool", "--backend", "uinput", *map(str, args)], capture_output=True, text=True, timeout=timeout, env=WDOTOOL_ENV)
        except subprocess.TimeoutExpired:
            _input_blocked_until[0] = time.time() + 60
            return PERMISSION_PENDING
        except OSError as e:
            return str(e)
    _input_blocked_until[0] = 0.0
    return (r.stdout + r.stderr).strip()


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


_own_input = [0.0, 0.0]  # when Jarvis's latest pointer move, click, typing or scroll started and ended (see user_idle)
_user_input = [0.0]  # when the user's own latest input was, seen just before Jarvis's (which hides it from the desktop)


def _was_mine(idle):
    """Whether the latest input, idle seconds ago, was Jarvis's own (Wayland says "in use" for 2 s after any input)."""
    return _own_input[0] - 1 <= time.time() - idle <= _own_input[1] + 2.5


def _mine(fn):
    """Input Jarvis makes itself, noted so it isn't taken for the user at the keyboard."""
    @functools.wraps(fn)
    def mine(*args, **kw):
        idle = _idle_seconds()
        if idle is not None and not _was_mine(idle):
            _user_input[0] = time.time() - idle
        _own_input[:] = [time.time(), float("inf")]
        try:
            return fn(*args, **kw)
        finally:
            _own_input[1] = time.time()
    return mine


@_mine
def move_pointer(px, py):
    """'' once the pointer is at (px, py) in screen pixels, else what went wrong."""
    if WAYLAND:
        if _wayland_tool() != "wdotool":
            return "moving the pointer on Wayland needs wdotool"
        for _ in range(3):  # wdotool makes a fresh virtual device per call: the first event is occasionally dropped
            out = _wdo("mousemove", px, py, timeout=30)  # (the first call waits while the user answers the permission prompt)
            if out:
                return out
            at = _wdo("getmouselocation")
            if at == f"x:{px} y:{py}":
                return ""
        return f"the pointer ended up at {at}"
    from pynput.mouse import Controller
    Controller().position = (px, py)
    return ""


@_mine
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


@_mine
def type_text(text):
    if WAYLAND:
        tool = _wayland_tool()
        return _wdo("type", "--", text, timeout=60) if tool == "wdotool" else run(["ydotool", "type", "--", text], 60) and "" if tool else \
            "typing on Wayland needs wdotool or ydotool"
    if IS_WINDOWS:
        return _send_text(text)
    from pynput.keyboard import Controller
    Controller().type(text)
    return ""


def _send_text(text):
    """Windows: the whole text in one SendInput call, each UTF-16 unit as a KEYEVENTF_UNICODE key down and up (so
    characters past the BMP go as their surrogate pair), line breaks as Enter and tabs as Tab (to the next field, as
    pynput did). pynput's key by key was slow and lost characters."""
    import ctypes

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16), ("dwFlags", ctypes.c_uint32),
                    ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):  # (only for the union's size: it's the biggest member)
        _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32), ("mouseData", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
                    ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_uint32), ("u", _U)]

    UNICODE, UP, KEYS = 0x0004, 0x0002, {"\n": 0x0D, "\t": 0x09}
    events = []
    for part in re.split(r"([\n\t])", re.sub(r"\r\n?", "\n", text)):
        if part in KEYS:
            events += [(KEYS[part], 0, 0), (KEYS[part], 0, UP)]
            continue
        units = part.encode("utf-16-le")
        for i in range(0, len(units), 2):
            unit = int.from_bytes(units[i:i + 2], "little")
            events += [(0, unit, UNICODE), (0, unit, UNICODE | UP)]
    if not events:
        return ""
    inputs = (INPUT * len(events))(*[INPUT(type=1, ki=KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags)) for vk, scan, flags in events])
    sent = ctypes.windll.user32.SendInput(len(events), inputs, ctypes.sizeof(INPUT))
    return "" if sent == len(events) else \
        f"Windows took {sent} of {len(events)} key events (a window running as administrator can't be typed into)"


@_mine
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


@_mine
def scroll(amount):
    if WAYLAND:
        return _wdo("scroll", "--", 0, int(amount), timeout=40) if _wayland_tool() == "wdotool" else "scrolling on Wayland needs wdotool"
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


def fullscreen():
    """Whether the focused window is full screen (a game, a film, a presentation)."""
    if IS_WINDOWS:  # (Windows' own answer: busy (a full-screen app), a full-screen Direct3D game, or presentation mode)
        import ctypes
        state = ctypes.c_int()
        return not ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) and state.value in (2, 3, 4)
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("kwinscript", "--inline", "output_result(String(!!workspace.activeWindow && workspace.activeWindow.fullScreen))") == "true"
    return False


_idle = {}  # Wayland: {"on": watching (False: can't), "since": when the keyboard and mouse were last left alone, or None}


def _idle_watch():
    """Wayland, on its own connection: the compositor says when the keyboard and mouse have been left alone for 2 s, and
    when they're used again (ext-idle-notify; v2's input-only kind, so a playing film doesn't count as the user)."""
    buf = b""
    try:
        sock = socket.socket(socket.AF_UNIX)
        sock.connect(os.path.join(os.environ.get("XDG_RUNTIME_DIR", ""), os.environ.get("WAYLAND_DISPLAY", "wayland-0")))

        def send(obj, op, *args):  # numbers, or strings (length, bytes, NUL, padded to 4)
            body = b""
            for a in args:
                a = struct.pack("<I", a) if isinstance(a, int) else struct.pack("<I", len(a) + 1) + a.encode() + b"\0" * (4 - len(a) % 4)
                body += a
            sock.sendall(struct.pack("<II", obj, (8 + len(body)) << 16 | op) + body)

        def events():
            nonlocal buf
            while True:
                if len(buf) >= 8 and len(buf) >= struct.unpack_from("<I", buf, 4)[0] >> 16:
                    obj, word = struct.unpack_from("<II", buf)
                    body, buf = buf[8:word >> 16], buf[word >> 16:]
                    if obj == 1 and word & 0xFFFF == 0:  # wl_display.error
                        raise OSError(body[12:].rstrip(b"\0").decode(errors="replace"))
                    yield obj, word & 0xFFFF, body
                    continue
                data = sock.recv(4096)
                if not data:
                    raise OSError("the compositor closed the connection")
                buf += data
        send(1, 1, 2)  # wl_display.get_registry -> 2
        send(1, 0, 3)  # wl_display.sync -> 3, done once every global has been listed
        found = {}
        for obj, op, body in events():
            if obj == 2 and op == 0:  # wl_registry.global: name, interface, version
                name, n = struct.unpack_from("<II", body)
                found[body[8:8 + n - 1].decode()] = (name, struct.unpack_from("<I", body, 8 + (n + 3) // 4 * 4)[0])
            elif obj == 3:
                break
        seat, notifier = found["wl_seat"], found["ext_idle_notifier_v1"]
        send(2, 0, seat[0], "wl_seat", 1, 4)  # wl_registry.bind -> 4
        send(2, 0, notifier[0], "ext_idle_notifier_v1", min(notifier[1], 2), 5)
        send(5, 2 if notifier[1] >= 2 else 1, 6, 2000, 4)  # get_input_idle_notification (v1: get_idle_notification) -> 6
        _idle["on"] = True
        for obj, op, body in events():
            if obj == 6:  # idled (0) or resumed (1)
                _idle["since"] = time.time() - 2 if op == 0 else None
    except (OSError, KeyError, struct.error) as e:
        print(f"[idle] can't tell when the keyboard and mouse are used: {e!r}", flush=True)
        _idle["on"] = False


def _idle_seconds():
    """Seconds since the keyboard or mouse was last used (by anyone), None if this desktop can't tell."""
    if IS_WINDOWS:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO))
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000
    if WAYLAND:
        if not _idle:
            _idle.update(on=None, since=None)
            threading.Thread(target=_idle_watch, daemon=True).start()
        if _idle["on"] is not False:  # (still connecting counts as in use)
            return 0.0 if _idle["since"] is None else time.time() - _idle["since"]
    out = run(["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.IdleMonitor", "--object-path",
               "/org/gnome/Mutter/IdleMonitor/Core", "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"], 3) if GNOME else \
        run(["xprintidle"], 3) if not WAYLAND and have("xprintidle") else ""
    m = re.fullmatch(r"\(uint64 (\d+),\)|(\d+)", out)
    return int(m[1] or m[2]) / 1000 if m else None


def user_idle():
    """Seconds since the user last used the keyboard or mouse, None when this desktop can't tell. When the latest input
    was Jarvis's own, it's the user's from just before it (inf if none was seen: they haven't been seen since)."""
    idle = _idle_seconds()
    if idle is None:
        return None
    if _was_mine(idle):
        return time.time() - _user_input[0] if _user_input[0] else float("inf")
    return idle


def focused():
    """(app, title) of the focused window, cheaply (for the screen history: called every few seconds); ("", "") if unknown."""
    if IS_WINDOWS:
        import ctypes, psutil
        user32, hwnd = ctypes.windll.user32, ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return "", ""
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            app = psutil.Process(pid.value).name().removesuffix(".exe")
        except Exception:
            app = ""
        return app, title.value
    if KDE and WAYLAND and have("kdotool"):
        out = _kdo("getactivewindow", "getwindowclassname", "getwindowname").split("\n", 1)
        return (out[0].split(".")[-1], out[1].strip()) if len(out) == 2 else ("", "")
    if WAYLAND:
        return "", ""
    import pywinctl
    w = pywinctl.getActiveWindow()
    return ((w.getAppName() or "").removesuffix(".exe"), w.title) if w else ("", "")


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
    if KDE and WAYLAND and have("kdotool"):  # one call for all of them (each kdotool call costs ~0.3 s)
        # (not stripped: a window with no title, like the desktop's own, is an empty line, and the last ones were lost)
        out = run(["kdotool", "search", ".", "getwindowclassname", "%@", "getwindowname", "%@"], strip=False).split("\n")[:-1]
        if len(out) % 2 == 0:
            n = len(out) // 2
            return [f"{app}: {title}" for app, title in zip(out[:n], out[n:])]
        return [f"{_kdo('getwindowclassname', wid)}: {_kdo('getwindowname', wid)}" for wid in _kdo("search", ".").split()]  # (a title with a line break)
    if WAYLAND:
        return ["(listing windows isn't possible on this Wayland desktop; look at the screen instead)"]
    import pywinctl
    return [f"{w.getAppName()}: {w.title}" for w in pywinctl.getAllWindows() if w.title]


def _find_windows(name):
    want = name.split(": ", 1)[-1].lower()
    if not want.strip():  # an empty name matches every window (close_window would close them all)
        return []
    import pywinctl
    return [w for w in pywinctl.getAllWindows() if want in w.title.lower() or want in (w.getAppName() or "").lower()]


def _kde_window(name, action):
    """kdotool's action on the first window matching name: '' when done, else the problem. (kdotool says nothing when no
    window matches, so the match's class name is printed first to tell.)"""
    if not name.split(": ", 1)[-1].strip():  # (an empty name matches every window)
        return "no window name given"
    # kdotool pastes the pattern into a KWin script as-is: a quote or backtick there breaks the script (a 5 s timeout
    # and an "Error:" line), so those match any character instead
    pattern = re.sub(r'["`]', ".", re.escape(name.split(": ", 1)[-1]))
    found = _kdo("search", pattern, "getwindowclassname", action)
    return "" if found and not found.startswith("Error") else f"no window matching {name}"


def focus_window(name, wid=None):
    """Bring a window to the front by (part of) its title or app name, or by id; '' when done, else the problem."""
    if KDE and WAYLAND and have("kdotool"):
        return _kdo("windowactivate", wid) if wid else _kde_window(name, "windowactivate")
    if WAYLAND:
        return "switching windows isn't possible on this Wayland desktop; use keyboard shortcuts (alt+tab)"
    import pywinctl
    found = [w for w in pywinctl.getAllWindows() if str(w.getHandle()) == wid] if wid else _find_windows(name)
    if not found:
        return f"no window matching {name}"
    found[0].activate()
    return ""


def app_running(name):
    """A program by that name (Vesktop, vesktop.exe) is running, with or without a window (an app in the tray has none)."""
    import psutil
    name = name.split(": ", 1)[-1].strip().lower().removesuffix(".exe")
    return bool(name) and any((p.info["name"] or "").lower().removesuffix(".exe") == name for p in psutil.process_iter(["name"]))


def vesktop():
    """Vesktop's main process (psutil), or None."""
    import psutil
    for p in psutil.process_iter(["cmdline"]):
        cmd = p.info["cmdline"] or []
        if cmd and not any(a.startswith("--type=") for a in cmd) and (
                os.path.basename(cmd[0]).lower() in ("vesktop", "vesktop.exe") or any(a.endswith("vesktop/app.asar") for a in cmd)):
            return p
    return None


def restart_vesktop(flag):
    """Quit Vesktop and start it again with a Chromium flag; on Linux packages whose launcher reads vesktop-flags.conf
    (Arch's), the flag goes there too, so it's on at every later start, and into Vesktop's own login entry (it runs
    Electron directly, so after a reboot the launcher's file isn't read)."""
    p = vesktop()
    minimized = bool(p) and "--start-minimized" in p.cmdline()
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    entry = os.path.join(config, "autostart", "vesktop.desktop")
    if not IS_WINDOWS and os.path.exists(entry):
        lines = open(entry).read().splitlines()
        if not any(line.startswith("Exec=") and flag in line.split() for line in lines):
            with open(entry, "w") as f:
                f.write("".join((line + " " + flag if line.startswith("Exec=") else line) + "\n" for line in lines))
    if IS_WINDOWS:
        exe = p.exe() if p else os.path.expandvars(r"%LOCALAPPDATA%\Programs\vesktop\Vesktop.exe")
        command = [exe]
    elif have("vesktop"):
        command = ["vesktop"]
        conf = os.path.join(config, "vesktop-flags.conf")
        with open(shutil.which("vesktop"), "rb") as f:
            reads_conf = b"vesktop-flags.conf" in f.read(200000)
        text = open(conf).read() if os.path.exists(conf) else ""
        if reads_conf and flag not in text.splitlines():
            with open(conf, "w") as f:
                f.write(text + ("\n" if text and not text.endswith("\n") else "") + flag + "\n")
    elif have("flatpak"):
        command = ["flatpak", "run", "dev.vencord.Vesktop"]
    else:
        raise RuntimeError("Vesktop isn't installed")
    if p:
        p.terminate()
        try:
            p.wait(15)
        except Exception:
            p.kill()
    command += ["--start-minimized"] * minimized + [flag]
    if IS_WINDOWS:
        subprocess.Popen(command, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def close_window(name):
    if KDE and WAYLAND and have("kdotool"):
        return _kde_window(name, "windowclose")
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


def swap_in_after_exit(new, install, args):
    """Windows (Jarvis.exe updating itself): a small script waits for this process to end, puts the new build's files
    over the install (Jarvis.exe and its _internal folder are replaced whole, nothing else there is touched), starts
    Jarvis.exe again with args and cleans up after itself. If either can't be moved aside, nothing is copied; if the
    copy fails, both old ones come back. Either way the old Jarvis starts and the download stays."""
    pid, staging = os.getpid(), os.path.dirname(new)
    old, exe = os.path.join(install, "_internal"), os.path.join(install, "Jarvis.exe")
    script = os.path.join(tempfile.gettempdir(), "jarvis-update.cmd")
    with open(script, "w", encoding="utf-8") as f:
        f.write(f'''@echo off
chcp 65001 >NUL
:wait
tasklist /FI "PID eq {pid}" /NH 2>NUL | find " {pid} " >NUL && (ping -n 2 127.0.0.1 >NUL & goto wait)
if exist "{old}.old" rmdir /s /q "{old}.old"
if exist "{exe}.old" del /f /q "{exe}.old"
if exist "{old}.old" goto start
if exist "{exe}.old" goto start
move "{old}" "{old}.old" >NUL || goto start
move "{exe}" "{exe}.old" >NUL || (move "{old}.old" "{old}" >NUL & goto start)
robocopy "{new}" "{install}" /E /R:10 /W:1 /NFL /NDL /NJH /NJS >NUL
if errorlevel 8 goto undo
rmdir /s /q "{old}.old"
del /f /q "{exe}.old"
rmdir /s /q "{staging}"
goto start
:undo
rmdir /s /q "{old}"
del /f /q "{exe}"
move "{old}.old" "{old}" >NUL
move "{exe}.old" "{exe}" >NUL
:start
start "" "{exe}" {subprocess.list2cmdline(args)}
(goto) 2>NUL & del "%~f0"
''')
    subprocess.Popen(["cmd", "/c", script], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) |
                     getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0), stdin=subprocess.DEVNULL,
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
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                **({} if IS_WINDOWS else {"start_new_session": True}))
        try:
            code = proc.wait(timeout)
        except subprocess.TimeoutExpired:  # all of it stops: a pipeline's or a sequence's other parts ran on after "timed
            _kill_tree(proc)  # out" (the build ran twice when asked again; a risky part finishing later was never logged)
            proc.wait()
            raise
        log.seek(0)
        return code, log.read().decode(errors="replace").strip()


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
        # ("--": a text starting with a dash, like a task's bulleted answer, was taken for an option and never shown)
        subprocess.Popen(["notify-send", "-a", "Jarvis", "-i", os.path.join(HERE, "icon.svg"), "--", title, text], stderr=subprocess.DEVNULL)
    elif notifier[0]:
        notifier[0](title, text)


def selected_text():
    """(the text selected right now, the clipboard): Linux has both; Windows has only the clipboard, so selected is ''."""
    def out(args, timeout=3):  # what the tool printed, only when it worked ("No selection" is its error, not the text)
        try:
            r = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=timeout,
                               creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return r.stdout.strip() if r.returncode == 0 else ""
    if IS_WINDOWS:
        return "", out(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], 5)
    if WAYLAND and have("wl-paste"):
        return out(["wl-paste", "--no-newline", "--primary"]), out(["wl-paste", "--no-newline"])
    if have("xclip"):
        return out(["xclip", "-o", "-selection", "primary"]), out(["xclip", "-o", "-selection", "clipboard"])
    return "", ""


def paste_text(text):
    """Puts text in the clipboard, presses ctrl+v, then puts back what the clipboard held: '' when done, else the
    problem; None where there's no clipboard tool (Windows, or Linux without wl-copy/xclip), so it's typed instead."""
    if WAYLAND and have("wl-copy"):
        copy, paste = ["wl-copy"], ["wl-paste", "--no-newline"]
    elif not IS_WINDOWS and have("xclip"):
        copy, paste = ["xclip", "-selection", "clipboard"], ["xclip", "-o", "-selection", "clipboard"]
    else:
        return None
    before = subprocess.run(paste, capture_output=True, timeout=3)  # (stdout only: an empty clipboard's error isn't text to keep)
    subprocess.run(copy, input=text.encode(), timeout=5)
    problem = press_keys("ctrl+v")
    time.sleep(0.5)  # (the app reads the clipboard after the key press)
    if before.returncode == 0 and before.stdout:
        subprocess.run(copy, input=before.stdout, timeout=5)
    return problem


# Windows' media controls (GlobalSystemMediaTransportControls) through Windows PowerShell's WinRT access (PowerShell 7
# has none). It stays running and answers each line it reads with one line of JSON about the session that's playing
# (else the one Windows calls current, else the first): '' for its details, or the method to call on it. Non-ASCII
# goes out as \u escapes, whatever the console's code page.
WIN_MEDIA = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | select -First 1
function Await($op, [type]$type) { $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); if ($task.Wait(1500)) { $task.Result } }
$M = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType=WindowsRuntime]
while ($null -ne ($action = [Console]::In.ReadLine())) {
    $out = @{}
    try {
        $manager = Await ($M::RequestAsync()) $M
        $all = @($manager.GetSessions())
        $s = $all | ? { $_.GetPlaybackInfo().PlaybackStatus -eq 'Playing' } | select -First 1
        if (-not $s) { $s = $manager.GetCurrentSession() }
        if (-not $s) { $s = $all | select -First 1 }
        if ($s -and $action) { $out = @{done = [bool](Await ($s.$action()) ([bool]))} } elseif ($s) {
            $p = Await ($s.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
            if ($p.Title -ne $lastTitle -or -not $art) {  # (the cover is read again only for a new song: it's the slow part)
                $lastTitle, $art = $p.Title, ''
                try {
                    $r = Await ($p.Thumbnail.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime])
                    $bytes = New-Object IO.MemoryStream
                    [IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($r).CopyTo($bytes)
                    $art = [Convert]::ToBase64String($bytes.ToArray())
                } catch {}
            }
            $t = $s.GetTimelineProperties()
            $out = @{player = $s.SourceAppUserModelId; status = [string]$s.GetPlaybackInfo().PlaybackStatus; title = [string]$p.Title
                     artist = [string]$p.Artist; art = $art; length = ($t.EndTime - $t.StartTime).TotalSeconds}
        }
    } catch {}
    [Console]::Out.WriteLine([regex]::Replace(($out | ConvertTo-Json -Compress), '[^\x00-\x7f]', { param($m) '\u{0:x4}' -f [int]$m.Value[0] }))
    [Console]::Out.Flush()
}
"""
_media_shell, _media_lock = [None], threading.Lock()  # (kept running: starting one each time the Today page asks costs a second of CPU)
_media_last, MEDIA_WAIT = [{}], 6  # the last answer about what's playing; seconds an answer may take
_art = [""]  # the cover art file now_playing wrote last
_web_cover = ["", ""]  # a player's cover on the web (Spotify's): its address, and the file it was saved as ("": none)


def _art_file(data):
    """The cover as a file the window can show, kept until the next one."""
    import hashlib, pathlib
    path = os.path.join(tempfile.gettempdir(), f"jarvis-art-{hashlib.sha1(data).hexdigest()[:12]}")
    if path != _art[0]:
        with open(path, "wb") as f:
            f.write(data)
        try:
            _art[0] and os.remove(_art[0])
        except OSError:  # (gone already, or the window still reading it)
            pass
        _art[0] = path
    return pathlib.Path(path).as_uri()


def _web_art(url):
    """A cover on the web, fetched once into a file: the window loads local files only (see window.LocalOnly)."""
    if url != _web_cover[0]:
        import requests
        art = ""
        try:
            with requests.get(url, timeout=5, stream=True) as r:
                data = r.raw.read(5_000_000, decode_content=True)
                if r.ok and r.headers.get("content-type", "").startswith("image/") and data:
                    art = _art_file(data)
        except (requests.RequestException, OSError, ValueError):
            pass
        _web_cover[:] = [url, art]
    return _web_cover[1]


def _win_media(action=""):
    """WIN_MEDIA's answer to one line ({} when there's no session or it failed); its PowerShell has no console window.
    One that takes over MEDIA_WAIT seconds (a player stuck answering) is ended, and the next call starts a fresh one;
    a poll while another call waits gets the last answer, so the Today page's polls can't pile up."""
    import base64, queue
    if not _media_lock.acquire(timeout=MEDIA_WAIT if action else 0):
        return {} if action else _media_last[0]
    try:
        for _ in range(2):  # (again with a fresh PowerShell when the last one has gone)
            try:
                shell = _media_shell[0]
                if not shell or shell.poll() is not None:
                    shell = _media_shell[0] = subprocess.Popen(
                        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", base64.b64encode(WIN_MEDIA.encode("utf-16-le")).decode()],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                        creationflags=0x08000000)  # (CREATE_NO_WINDOW)
                    shell.lines = queue.Queue()  # (read on a thread, so the wait for an answer has a limit; '' when it ends)
                    threading.Thread(target=lambda s=shell: [s.lines.put(line) for line in s.stdout] + [s.lines.put("")], daemon=True).start()
                shell.stdin.write(action + "\n")
                shell.stdin.flush()
                answer = json.loads(shell.lines.get(timeout=MEDIA_WAIT))
                if not action:
                    _media_last[0] = answer
                return answer
            except queue.Empty:
                shell.kill()
                _media_shell[0] = None
                break
            except (OSError, ValueError):
                pass
        return {}
    finally:
        _media_lock.release()


def _windows_playing():
    info = _win_media()
    if not info.get("player"):
        return {}
    app = re.sub(r"\.exe$", "", info["player"].split("!")[-1], flags=re.I).split(".")[-1]  # Spotify.exe, ...!Microsoft.ZuneMusic
    import base64
    art = _art_file(base64.b64decode(info["art"])) if info.get("art") else ""
    return {"player": info["player"], "app": app[:1].upper() + app[1:], "status": info.get("status") or "",
            "title": info.get("title") or "", "artist": info.get("artist") or "", "art": art, "length": info.get("length") or 0}


def now_playing():
    """The media player that's playing (or the first one): {player, app, status, title, artist, art, length}. Linux
    (MPRIS) and Windows (its media controls)."""
    if IS_WINDOWS:
        return _windows_playing()
    if not have("busctl"):
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
    if re.match(r"https?://", best.get("art", ""), re.I):
        best["art"] = _web_art(best["art"])
    return best


def media(action):
    """PlayPause, Next or Previous for the current player (media keys where MPRIS or Windows' media controls can't)."""
    if IS_WINDOWS:
        if _win_media({"PlayPause": "TryPlayPauseAsync", "Next": "TrySkipNextAsync", "Previous": "TrySkipPreviousAsync"}[action]).get("done"):
            return
    elif player := now_playing().get("player"):
        run(["busctl", "--user", "call", player, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", action], 5)
        return
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
        body = f'@echo off\r\nchcp 65001 >NUL\r\nstart "" {command}\r\n'  # (UTF-8: a user name like José is in the path)
    else:
        path = os.path.expanduser("~/.config/autostart/jarvis.desktop")
        body = (f"[Desktop Entry]\nType=Application\nName=Jarvis\nExec={command}\nIcon={os.path.join(HERE, 'icon.svg')}\n"
                "X-KDE-autostart-phase=2\nTerminal=false\n")
    if enabled:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
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
