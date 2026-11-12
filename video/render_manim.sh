#!/bin/sh
# Renders the Manim diagram to public/how.mp4 (1080p60, near-lossless: it's laid over the trailer with a screen blend).
# Manim's png-sequence writes one frame for a wait, so the opening pause and the closing hold are put back here.
set -e
cd "$(dirname "$0")"
rm -rf manim/media
manim/.venv/bin/manim -qh --fps 60 --format png-sequence -0 5 --media_dir manim/media manim/how_it_works.py HowItWorks >/dev/null 2>&1
ffmpeg -v error -y -framerate 60 -pattern_type glob -i 'manim/media/images/how_it_works/HowItWorks/*.png' \
  -vf tpad=start_mode=clone:start_duration=0.15:stop_mode=clone:stop_duration=2.5 \
  -c:v libx264 -crf 12 -preset slow -pix_fmt yuv420p -movflags +faststart public/how.mp4
ffprobe -v error -show_entries format=duration:stream=width,height,nb_frames -of csv=p=0 public/how.mp4
