# The trailer

A 46-second, 1080p60 trailer for Jarvis. Remotion puts it together (`src/`), Manim draws the "how it works" diagram
(`manim/how_it_works.py`), the app's own pages are the footage (`public/screens`, made-up data) and the music and
sound effects are generated (`audio/make_audio.py`: nothing licensed or downloaded).

```bash
npm i                                            # once
npm run dev                                      # Remotion Studio: preview and edit
npx remotion render JarvisTrailer out/jarvis-trailer.mp4 --crf=16 --jpeg-quality=95
```

Rebuilding the parts (only after changing them):

```bash
# the app's pages, at 2x so zooms stay sharp (from the repo root)
QT_SCALE_FACTOR=2 .venv/bin/python docs/screens.py video/public/screens home accounts memory settings
# the diagram -> public/how.mp4 (once: uv venv manim/.venv --python 3.13 && uv pip install --python manim/.venv/bin/python manim)
./render_manim.sh
# the soundtrack -> public/audio
manim/.venv/bin/python audio/make_audio.py
```

- Scenes change on the music's bar lines: `src/timing.ts` and `BARS`/`HITS` in `audio/make_audio.py` hold the same
  numbers. Move a cut in both.
- Colours and type are the app's (`qml/Theme.qml`, Inter); `src/Orb.tsx` is `qml/Orb.qml` as SVG.
- Manim: `--format png` writes only the last frame; `png-sequence` writes them all but one frame per `wait`, which
  `render_manim.sh` pads back.
- `interpolateColors` returns `rgba(...)`, not hex: `theme.ts`'s `rgba`/`lighter` take both.
