import type {CSSProperties} from 'react';
import {useId} from 'react';
import {C, lighter, rgba} from './theme';

// `n` arcs, each `fill` (0-1) of its share of a circle of radius `rad` around the origin.
const arcs = (rad: number, n: number, fill: number) => {
  let d = '';
  for (let i = 0; i < n; i++) {
    const a0 = (i * 2 * Math.PI) / n - Math.PI / 2;
    const a1 = a0 + (fill * 2 * Math.PI) / n;
    d += `M ${rad * Math.cos(a0)} ${rad * Math.sin(a0)} A ${rad} ${rad} 0 0 1 ${rad * Math.cos(a1)} ${rad * Math.sin(a1)} `;
  }
  return d;
};

type Props = {
  readonly size: number;
  readonly tint?: string;
  readonly spin?: number; // the segmented ring's angle, degrees
  readonly pulse?: number; // how far it swells: 0.015 breathing, up to ~0.15 with a voice
  readonly rings?: boolean; // false: the small one (rail, notch)
  readonly power?: number; // 0-1: the core and its bloom
  readonly draw?: number; // 0-1: the rings drawing themselves
  readonly style?: CSSProperties;
};

// Jarvis's face, the arc reactor: qml/Orb.qml drawn as SVG, radius for radius.
export const Orb = ({size, tint = C.accent, spin = 0, pulse = 0.015, rings = true, power = 1, draw = 1, style}: Props) => {
  const id = useId().replace(/[^a-zA-Z0-9]/g, '');
  const r = size / 2;
  const u = Math.max(1, size / 220);
  const inner = r * (rings ? 0.5 : 0.66) * (1 + pulse * 0.5);
  return (
    <svg width={size} height={size} viewBox={`${-r} ${-r} ${size} ${size}`} style={{overflow: 'visible', ...style}}>
      <defs>
        <radialGradient id={`halo${id}`}>
          <stop offset={0.2} stopColor={rgba(tint, rings ? 0.25 : 0.22)} />
          <stop offset={rings ? 0.62 : 0.5} stopColor={rgba(tint, rings ? 0.12 : 0.06)} />
          <stop offset={rings ? 0.82 : 0.75} stopColor={rgba(tint, rings ? 0.045 : 0.02)} />
          <stop offset={1} stopColor={rgba(tint, 0)} />
        </radialGradient>
        <radialGradient id={`disc${id}`}>
          <stop offset={0.6} stopColor={rgba(tint, 0.45)} />
          <stop offset={1} stopColor={rgba(tint, 0.08)} />
        </radialGradient>
        <radialGradient id={`core${id}`}>
          <stop offset={0} stopColor="white" />
          <stop offset={0.22} stopColor="white" />
          <stop offset={0.5} stopColor={lighter(tint, 0.3)} />
          <stop offset={0.85} stopColor={tint} />
          <stop offset={1} stopColor={rgba(tint, 0.85)} />
        </radialGradient>
      </defs>
      <circle r={r * (rings ? 1.35 : 1) * (1 + pulse * 2.2)} fill={`url(#halo${id})`} opacity={0.25 * draw + 0.75 * power} />
      {rings ? (
        <g fill="none">
          <circle
            r={r * 0.84}
            stroke={rgba(tint, 0.3)}
            strokeWidth={u}
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - draw}
            transform="rotate(-90)"
          />
          <circle r={r * 0.65} stroke={rgba(tint, 0.1)} strokeWidth={Math.max(2, r * 0.05)} opacity={draw} />
          <path
            d={arcs(r * 0.65, 12, 0.7)}
            stroke={rgba(tint, 0.7)}
            strokeWidth={Math.max(2, r * 0.05)}
            opacity={draw}
            transform={`rotate(${spin})`}
          />
        </g>
      ) : null}
      <g opacity={power} style={{filter: `drop-shadow(0 0 ${r * 0.22}px ${rgba(tint, 0.55)})`}}>
        <circle r={inner} fill={`url(#disc${id})`} />
        <circle r={inner} fill="none" stroke={rgba(tint, 0.95)} strokeWidth={(rings ? 2 : 1.5) * u} />
        <circle r={r * (rings ? 0.33 : 0.44) * (1 + pulse)} fill={`url(#core${id})`} />
      </g>
    </svg>
  );
};
