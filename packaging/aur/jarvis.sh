#!/bin/sh
# Jarvis from the AUR. The app is in /opt/jarvis-assistant; its Python packages (most aren't in Arch's repos) go in each
# user's own venv, which uv makes on the first start and brings up to date when an update changes requirements.txt.
APP=/opt/jarvis-assistant
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/jarvis-assistant"
VENV="$CACHE/venv"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/jarvis"
say() { command -v notify-send >/dev/null && notify-send -a Jarvis -i jarvis-assistant Jarvis "$1"; echo "$1" >&2; }

if ! cmp -s "$APP/requirements.txt" "$VENV/requirements.txt"; then
    say "Getting Jarvis's Python packages ready (a minute or two)..."
    { [ -x "$VENV/bin/python" ] || uv venv -q --python 3.13 "$VENV"; } &&
        uv pip install -q --python "$VENV/bin/python" -r "$APP/requirements.txt" &&
        uv pip install -q --python "$VENV/bin/python" --no-deps openwakeword &&  # (its tflite dependency has no current wheels)
        cp "$APP/requirements.txt" "$VENV/requirements.txt" ||
        { say "Couldn't get Jarvis's Python packages: run  jarvis  in a terminal to see why."; exit 1; }
fi
export PYTHONPYCACHEPREFIX="$CACHE/pycache"  # (/opt isn't writable)
# KDE: the packaged screenshot helper, where Jarvis looks for it (unless install.sh built one there)
[ -e "$DATA/bin/jarvis-shot" ] || { mkdir -p "$DATA/bin" && ln -sf /usr/lib/jarvis-assistant/jarvis-shot "$DATA/bin/jarvis-shot"; }

case "$(systemctl --user is-system-running 2>/dev/null)" in running|degraded)
    # its own "app-jarvis" scope, so the desktop knows the app as "jarvis" (KDE's input permission is per app)
    exec systemd-run --user --scope --quiet --collect --unit="app-jarvis-$$" "$VENV/bin/python" "$APP/jarvis.py" "$@"
esac
exec "$VENV/bin/python" "$APP/jarvis.py" "$@"
