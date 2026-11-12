"""How Jarvis works, as a diagram: you -> wake word (on your PC) -> live voice -> agent -> tools.

Drawn on black so the trailer can lay it over its own background (screen blend). Render:

    manim/.venv/bin/manim -qh --fps 60 --format png -o how manim/how_it_works.py HowItWorks   (see ../render.sh)
"""
import os

from manim import (BLACK, DOWN, LEFT, RIGHT, UP, Create, CubicBezier, DashedVMobject, FadeIn, LaggedStart, Line,
                   Rectangle, RoundedRectangle, Scene, ShowPassingFlash, Succession, Text, VGroup, config, rate_functions)
from manimpango import register_font

register_font(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "InterVariable.ttf"))
config.background_color = BLACK
FONT = "Inter Variable"
CYAN, WARM, TEXT, DIM = "#3fd8ff", "#ff9d3f", "#eaf6ff", "#93a9b9"
OUT = rate_functions.ease_out_quart
Y = -0.75  # the diagram's middle: the trailer's headline sits above it


def label(text, size, color=TEXT, weight="MEDIUM"):
    return Text(text, font=FONT, font_size=size, color=color, weight=weight)


def node(title, sub, x, color=CYAN, width=2.1):
    box = RoundedRectangle(width=width, height=1.25, corner_radius=0.24, stroke_color=color, stroke_width=2.2,
                           stroke_opacity=0.7, fill_color=color, fill_opacity=0.06)
    glow = box.copy().set_stroke(color, width=10, opacity=0.1).set_fill(opacity=0)
    words = VGroup(label(title, 25, weight="SEMIBOLD"), label(sub, 16, DIM)).arrange(DOWN, buff=0.14)
    return VGroup(glow, box, words).move_to([x, Y, 0])


def wire(a, b):
    return Line(a.get_right(), b.get_left(), stroke_color=CYAN, stroke_width=2, stroke_opacity=0.4, buff=0.12)


def flash(path, color=CYAN, run_time=0.55):
    return ShowPassingFlash(path.copy().set_stroke(color, width=5, opacity=1), time_width=0.45, run_time=run_time,
                            rate_func=rate_functions.ease_in_out_sine)


class HowItWorks(Scene):
    def construct(self):
        # you: a little voice waveform and what you said
        bars = VGroup(*[Rectangle(width=0.085, height=h, stroke_width=0, fill_color=CYAN, fill_opacity=0.95)
                        .round_corners(0.04) for h in (0.3, 0.62, 0.95, 0.5, 0.78, 0.36)]).arrange(RIGHT, buff=0.085)
        said = label("“Hey Jarvis”", 23, weight="SEMIBOLD")
        you = VGroup(bars, said).arrange(DOWN, buff=0.26).move_to([-5.15, Y, 0])

        wake = node("Wake word", "found on your PC", -2.9)
        voice = node("Live voice", "hears and speaks", 0)
        agent = node("Agent", "plans the work", 2.7, WARM, width=1.9)
        tools = VGroup(*[self.chip(t) for t in ("Web", "Accounts", "Desktop", "Shell", "Phone")])
        tools.arrange(DOWN, buff=0.2).move_to([5.2, Y, 0])

        fence = DashedVMobject(RoundedRectangle(width=4.45, height=2.5, corner_radius=0.34).move_to([-3.825, Y, 0]),
                               num_dashes=64, dashed_ratio=0.5).set_stroke(CYAN, width=1.6, opacity=0.5)
        fence_name = label("STAYS ON YOUR PC", 14, CYAN, "SEMIBOLD").next_to(fence, UP, buff=0.16).align_to(fence, LEFT).shift(RIGHT * 0.3)

        w1 = Line(you.get_right(), wake.get_left(), stroke_color=CYAN, stroke_width=2, stroke_opacity=0.4, buff=0.1)
        w2, w3 = wire(wake, voice), wire(voice, agent)
        fans = VGroup(*[self.fan(agent, t) for t in tools])

        def enter(mob, **kw):
            return FadeIn(mob, shift=UP * 0.12, scale=0.96, rate_func=OUT, run_time=0.5, **kw)

        self.wait(0.15)
        self.play(LaggedStart(*[FadeIn(b, scale=0.4, rate_func=OUT) for b in bars], lag_ratio=0.12, run_time=0.5),
                  FadeIn(said, shift=UP * 0.1, rate_func=OUT, run_time=0.5))
        self.play(Create(w1, rate_func=OUT, run_time=0.4), enter(wake),
                  Create(fence, rate_func=rate_functions.ease_in_out_cubic, run_time=0.8),
                  FadeIn(fence_name, rate_func=OUT, run_time=0.6))
        self.play(flash(w1, run_time=0.4))
        self.play(Create(w2, rate_func=OUT, run_time=0.4), enter(voice))
        self.play(Succession(flash(w2, run_time=0.4)), Create(w3, rate_func=OUT, run_time=0.4), enter(agent))
        self.play(flash(w3, WARM, 0.4),
                  LaggedStart(*[Create(f, rate_func=OUT) for f in fans], lag_ratio=0.1, run_time=0.7),
                  LaggedStart(*[enter(t) for t in tools], lag_ratio=0.1, run_time=0.9))
        self.play(LaggedStart(*[flash(f, WARM, 0.6) for f in fans], lag_ratio=0.14, run_time=1.2),
                  LaggedStart(*[t[0].animate(rate_func=rate_functions.there_and_back, run_time=0.6)
                                .set_stroke(WARM, opacity=1).set_fill(WARM, opacity=0.2) for t in tools],
                              lag_ratio=0.14, run_time=1.3))
        # the answer comes back and is spoken
        back = Line(agent.get_left(), voice.get_right(), buff=0.12)
        self.play(flash(back, CYAN, 0.5),
                  voice[1].animate(rate_func=rate_functions.there_and_back, run_time=0.9).set_stroke(opacity=1).set_fill(opacity=0.22))
        self.wait(1.4)

    def chip(self, text):
        box = RoundedRectangle(width=1.7, height=0.52, corner_radius=0.26, stroke_color=CYAN, stroke_width=1.8,
                               stroke_opacity=0.55, fill_color=CYAN, fill_opacity=0.05)
        return VGroup(box, label(text, 18).move_to(box))

    def fan(self, agent, tool):
        a, b = agent.get_right() + RIGHT * 0.12, tool.get_left() + LEFT * 0.1
        bend = RIGHT * 0.45
        return CubicBezier(a, a + bend, b - bend, b).set_stroke(CYAN, width=1.8, opacity=0.38)
