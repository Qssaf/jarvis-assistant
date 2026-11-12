import type {CSSProperties, ReactNode} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, CLAMP, OUT, rgba} from './theme';

// What's behind every scene: the app's dark gradient, two slow drifting glows and a vignette.
// `offset` (frames) keeps a copy inside a scene in step with the one behind the whole trailer.
export const Backdrop = ({offset = 0}: {readonly offset?: number}) => {
  const frame = useCurrentFrame() + offset;
  const {fps} = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${C.bgTop} 0%, ${C.bg} 50%, ${C.bgBottom} 100%)`}}>
      <div
        style={{
          position: 'absolute',
          left: 60,
          top: -620,
          width: 1800,
          height: 1200,
          borderRadius: '50%',
          background: `radial-gradient(closest-side, ${rgba(C.accent, 0.11)}, ${rgba(C.accent, 0)})`,
          translate: `${Math.sin(t * 0.21) * 140}px ${Math.cos(t * 0.17) * 50}px`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 900,
          top: 520,
          width: 1500,
          height: 1100,
          borderRadius: '50%',
          background: `radial-gradient(closest-side, ${rgba('#1b9cc4', 0.08)}, ${rgba('#1b9cc4', 0)})`,
          translate: `${Math.cos(t * 0.19) * 120}px ${Math.sin(t * 0.23) * 60}px`,
        }}
      />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.4) 100%)'}} />
    </AbsoluteFill>
  );
};

type WordsProps = {
  readonly text: string;
  readonly at: number; // frame the first piece starts
  readonly stagger?: number; // frames between pieces
  readonly by?: 'word' | 'letter';
  readonly rise?: number;
  readonly tint?: (piece: string, i: number) => string | undefined;
  readonly style?: CSSProperties;
};

// Text that arrives piece by piece: each rises a little, sharpens and fades in.
export const Words = ({text, at, stagger = 4, by = 'word', rise = 26, tint, style}: WordsProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pieces = by === 'word' ? text.split(' ') : [...text];
  return (
    <div style={style}>
      {pieces.map((piece, i) => {
        const start = at + i * stagger;
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              whiteSpace: 'pre',
              color: tint?.(piece, i),
              opacity: interpolate(frame, [start, start + 0.45 * fps], [0, 1], OUT),
              translate: interpolate(frame, [start, start + 0.7 * fps], [`0px ${rise}px`, '0px 0px'], OUT),
              filter: `blur(${interpolate(frame, [start, start + 0.5 * fps], [8, 0], OUT)}px)`,
            }}
          >
            {piece + (by === 'word' && i < pieces.length - 1 ? ' ' : '')}
          </span>
        );
      })}
    </div>
  );
};

// A small tracked label above a headline.
export const Eyebrow = ({children, at, color = C.accent}: {readonly children: ReactNode; readonly at: number; readonly color?: string}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div
      style={{
        fontSize: 30,
        fontWeight: 600,
        letterSpacing: '0.22em',
        color,
        opacity: interpolate(frame, [at, at + 0.5 * fps], [0, 1], OUT),
        translate: interpolate(frame, [at, at + 0.6 * fps], ['0px 14px', '0px 0px'], OUT),
      }}
    >
      {children}
    </div>
  );
};

// A line at the bottom of the frame saying what the picture shows.
export const Caption = ({
  children,
  from,
  to,
  dot = C.accent,
}: {
  readonly children: ReactNode;
  readonly from: number;
  readonly to: number;
  readonly dot?: string;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 84,
        display: 'flex',
        justifyContent: 'center',
        opacity: interpolate(frame, [from, from + 0.4 * fps, to - 0.25 * fps, to], [0, 1, 1, 0], CLAMP),
        translate: interpolate(frame, [from, from + 0.6 * fps], ['0px 24px', '0px 0px'], OUT),
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          padding: '22px 44px 22px 36px',
          borderRadius: 999,
          background: C.panel,
          backdropFilter: 'blur(28px)',
          border: `1px solid ${C.strokeStrong}`,
          boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
          fontSize: 42,
          fontWeight: 500,
          letterSpacing: '-0.01em',
        }}
      >
        <div style={{width: 14, height: 14, borderRadius: 7, background: dot, boxShadow: `0 0 18px ${dot}`}} />
        {children}
      </div>
    </div>
  );
};
