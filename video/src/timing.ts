// Seconds. The music is 100 BPM (a bar is 2.4 s) and every scene takes over on a bar line: audio/make_audio.py
// puts its hits and risers on the same numbers.
export const CUTS = [0, 4.8, 9.6, 16.8, 26.4, 33.6, 40.8];
export const END = 46.2;
export const FADE = 0.4; // each scene fades into the next, centred on its cut
export const FPS = 60;

// How long each scene's sequence is, the fades included.
export const sceneSeconds = (i: number) =>
  i === 0 ? CUTS[1] + FADE / 2 : i === CUTS.length - 1 ? END - CUTS[i] + FADE / 2 : CUTS[i + 1] - CUTS[i] + FADE;

// When scene i's own clock starts, on the trailer's clock.
export const sceneStart = (i: number) => (i === 0 ? 0 : CUTS[i] - FADE / 2);
