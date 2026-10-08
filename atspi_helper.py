#!/usr/bin/python3
"""Reads and presses app controls through the accessibility interface (AT-SPI), by name: no screenshots, no mouse.
Runs under the system Python (it has the gi bindings) as a long-lived helper: one JSON command per stdin line,
one JSON reply per stdout line. Started by brain.py."""
import json, sys, time, warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)  # get_action_name: the replacement clashes in gi

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

INTERACTIVE = {"push button", "toggle button", "check box", "radio button", "menu item", "check menu item",
               "radio menu item", "text", "entry", "password text", "combo box", "link", "list item", "page tab",
               "spin button", "slider", "tree item", "table cell", "menu", "button"}
PRESS_GAP = 0.13  # Qt animates an accessibility press for ~100 ms; faster presses get lost


def apps():
    d = Atspi.get_desktop(0)
    return [a for a in (d.get_child_at_index(i) for i in range(d.get_child_count())) if a]


def names(app):
    """An app's accessible name and its process's name: Chromium browsers may call themselves something else."""
    try:
        with open(f"/proc/{app.get_process_id()}/comm") as f:
            return f"{app.get_name() or ''} {f.read().strip()}".lower()
    except Exception:
        return (app.get_name() or "").lower()


def find_app(name, wait=0.0):
    end = time.time() + wait
    want = name.lower().split(".")[-1]  # "org.kde.kcalc" -> "kcalc"
    while True:
        for a in apps():
            if want in names(a):
                return a
        if time.time() >= end:
            raise LookupError(f"no accessible app named '{name}': it isn't open, or it doesn't show its controls (browsers and "
                              "Electron apps like Discord or VS Code only do when Jarvis starts them), so use look and click_on "
                              f"instead. Apps with named controls: {', '.join(sorted({a.get_name() for a in apps() if a.get_name()}))}")
        time.sleep(0.1)


def walk(node, out, depth=0, limit=3000):
    if len(out) >= limit or depth > 40:
        return out
    try:
        role, name, n = node.get_role_name(), (node.get_name() or "").strip(), node.get_child_count()
        states = node.get_state_set()
        if states.contains(Atspi.StateType.DEFUNCT):
            return out
    except Exception:
        return out
    out.append((role, name, node, states))
    for i in range(min(n, 500)):
        c = node.get_child_at_index(i)
        if c:
            walk(c, out, depth + 1, limit)
    return out


def controls(app):
    seen, out = set(), []
    for role, name, node, states in walk(app, []):
        if role in INTERACTIVE and name and states.contains(Atspi.StateType.SHOWING) and (role, name) not in seen:
            seen.add((role, name))
            out.append((role, name, node))
    return out


def lookup(ctrls, name):
    low = name.lower().strip()
    for exact in (True, False):
        for role, n, node in ctrls:
            if (n.lower() == low) if exact else (low in n.lower()):
                return node
    return None


def do_press(node):
    act = node.get_action_iface()
    if act and act.get_n_actions():
        names = [(Atspi.Action.get_action_name(act, i) or "").lower() for i in range(act.get_n_actions())]
        best = next((i for i, n in enumerate(names) if n in ("press", "click", "activate", "toggle", "jump")), 0)
        return act.do_action(best)
    comp = node.get_component_iface()
    return comp.grab_focus() if comp else False


def handle(cmd):
    app = find_app(cmd["app"], wait=float(cmd.get("wait", 0)))
    if cmd["cmd"] == "controls":
        return {"app": app.get_name(), "controls": [f"{role}: {name}" for role, name, _ in controls(app)][:400]}
    if cmd["cmd"] == "press":
        ctrls, pressed = controls(app), []
        for name in cmd["names"]:
            node = lookup(ctrls, name)
            if node is None:
                return {"error": f"no control named '{name}'", "pressed": pressed,
                        "available": [f"{r}: {n}" for r, n, _ in ctrls][:200]}
            do_press(node)
            pressed.append(name)
            time.sleep(PRESS_GAP)
        return {"pressed": pressed}
    if cmd["cmd"] == "set_text":
        ctrls = controls(app)
        node = lookup(ctrls, cmd["field"]) if cmd.get("field") else next((n for r, _, n in ctrls if r in ("text", "entry")), None)
        if node is None:
            return {"error": f"no text field '{cmd.get('field', '')}'", "available": [f"{r}: {n}" for r, n, _ in ctrls][:200]}
        editable = node.get_editable_text_iface()
        if not editable:
            return {"error": "that field can't be edited directly; click it and use type instead"}
        editable.set_text_contents(cmd["text"])
        return {"set": cmd.get("field") or "first text field"}
    return {"error": f"unknown command {cmd['cmd']}"}


for line in sys.stdin:
    try:
        reply = handle(json.loads(line))
    except Exception as e:
        reply = {"error": str(e)[:500]}
    print(json.dumps(reply), flush=True)
