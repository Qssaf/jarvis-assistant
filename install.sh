#!/bin/sh
# Sets up Jarvis on Linux (any distro; X11 or Wayland): the Python environment, the `jarvis` command and the app-menu
# entry. Safe to run again. See the README for the system packages each desktop needs.
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/jarvis"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/jarvis"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

if ! command -v uv >/dev/null; then
    echo "Jarvis needs uv (https://docs.astral.sh/uv/). Install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
[ -d .venv ] || uv venv --python 3.13 .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
uv pip install -q --python .venv/bin/python --no-deps openwakeword  # (its tflite dependency has no current wheels)

mkdir -p "$HOME/.local/bin" "$APPS" "$CONFIG"
if command -v systemd-run >/dev/null && systemctl --user is-system-running >/dev/null 2>&1 ||
   [ "$(systemctl --user is-system-running 2>/dev/null)" = degraded ]; then
    # its own "app-jarvis" scope, so the desktop knows the app as "jarvis" (KDE's input permission is per app)
    RUN="systemd-run --user --scope --quiet --collect --unit=\"app-jarvis-\$\$\" "
else
    RUN=""
fi
cat > "$HOME/.local/bin/jarvis" <<EOF
#!/bin/sh
exec $RUN"$DIR/.venv/bin/python" "$DIR/jarvis.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/jarvis"

cat > "$APPS/jarvis.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Voice assistant (say "Hey Jarvis")
Exec=$HOME/.local/bin/jarvis
Icon=$DIR/icon.svg
Terminal=false
Categories=Utility;
StartupNotify=false
EOF

# KDE Plasma on Wayland: a tiny helper that alone gets KWin's screenshot permission (~30 ms instead of starting Spectacle)
case "$XDG_CURRENT_DESKTOP" in *KDE*)
    if command -v gcc >/dev/null && pkg-config --exists gio-unix-2.0 2>/dev/null; then
        mkdir -p "$DATA/bin"
        gcc -O2 -o "$DATA/bin/jarvis-shot" jarvis-shot.c $(pkg-config --cflags --libs gio-unix-2.0)
        cat > "$APPS/jarvis-screenshot.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis screenshot helper
Comment=Lets Jarvis's own screenshot helper (and nothing else) capture the screen through KWin
Exec=$DATA/bin/jarvis-shot
NoDisplay=true
X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2
EOF
        kbuildsycoca6 --noincremental >/dev/null 2>&1 || kbuildsycoca5 --noincremental >/dev/null 2>&1 || true  # (KWin only trusts the helper once it sees this file)
    else
        echo "(optional) install gcc and glib's development headers, then run this again, for 30 ms screenshots on KDE"
    fi
esac

# what this desktop still needs (nothing here is installed for you)
missing=""
need() { command -v "$1" >/dev/null || missing="$missing\n  - $1: $2"; }
if [ "$XDG_SESSION_TYPE" = wayland ]; then
    need wdotool "mouse and keyboard control on Wayland (or ydotool, which can type but not move the pointer)"
    case "$XDG_CURRENT_DESKTOP" in
        *KDE*) need kdotool "finding, focusing and closing windows on KDE"; need spectacle "screenshots" ;;
        *GNOME*) need gnome-screenshot "screenshots" ;;
        *) need grim "screenshots (wlroots desktops: Sway, Hyprland...)" ;;
    esac
    need wl-paste "clipboard access (wl-clipboard)"
else
    need xclip "clipboard access"
fi
command -v pw-record >/dev/null || python3 -c "import ctypes.util, sys; sys.exit(not ctypes.util.find_library('portaudio'))" 2>/dev/null ||
    missing="$missing\n  - PipeWire or PortAudio (libportaudio2 / portaudio): the microphone and speaker"
/usr/bin/python3 -c "import gi; gi.require_version('Atspi', '2.0')" 2>/dev/null ||
    missing="$missing\n  - python3-gi with AT-SPI (python3-gi + gir1.2-atspi-2.0, or python-gobject + at-spi2-core): pressing app buttons by name"
command -v chromium >/dev/null || command -v google-chrome >/dev/null || command -v chromium-browser >/dev/null ||
    missing="$missing\n  - chromium or google-chrome (optional): reading JavaScript-heavy web pages"
if [ -n "$missing" ]; then
    printf "Install these with your package manager for everything to work:%b\n" "$missing"
fi

if [ ! -f "$CONFIG/env" ]; then
    echo "Next: put your Google AI Studio key in $CONFIG/env as  GEMINI_API_KEY=...  (then: chmod 600 $CONFIG/env)"
fi
echo "Installed. Start Jarvis from the app menu or run: jarvis"
