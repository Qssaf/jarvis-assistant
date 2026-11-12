import {Easing} from 'remotion';

// The app's own look (qml/Theme.qml): near-black glass, Jarvis's cyan, orange while it works.
export const C = {
  bg: '#05080d',
  bgTop: '#08121c',
  bgBottom: '#04070b',
  text: '#eaf6ff',
  text2: '#93a9b9',
  text3: '#748b9c',
  accent: '#3fd8ff',
  listen: '#7cf0ff',
  warm: '#ff9d3f',
  red: '#f2545b',
  stroke: 'rgba(255,255,255,0.08)',
  strokeStrong: 'rgba(255,255,255,0.14)',
  glass: 'rgba(255,255,255,0.045)',
  panel: 'rgba(8,15,22,0.9)',
};

export const FONT = 'Inter Variable';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const CLAMP = clamp;
// entrances start fast and settle; things moving on screen ease both ways; the notch drops like a drawer
export const OUT = {...clamp, easing: Easing.bezier(0.23, 1, 0.32, 1)};
export const IN_OUT = {...clamp, easing: Easing.bezier(0.77, 0, 0.175, 1)};
export const DRAWER = {...clamp, easing: Easing.bezier(0.32, 0.72, 0, 1)};

// "#rrggbb" or the "rgba(r, g, b, a)" that interpolateColors gives
const channels = (color: string) => {
  if (color.startsWith('#')) {
    const n = parseInt(color.slice(1), 16);
    return [n >> 16, (n >> 8) & 255, n & 255];
  }
  return (color.match(/[\d.]+/g) ?? ['0', '0', '0']).slice(0, 3).map(Number);
};

export const rgba = (color: string, alpha: number) => `rgba(${channels(color).join(',')},${alpha})`;

export const lighter = (color: string, amount: number) =>
  `rgb(${channels(color)
    .map((c) => Math.round(c + (255 - c) * amount))
    .join(',')})`;
