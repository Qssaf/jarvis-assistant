import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Orb} from '../Orb';
import {Words} from '../parts';
import {C, CLAMP, OUT} from '../theme';

// What it is, in one line.
export const Title = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        scale: interpolate(frame, [0, durationInFrames], [1, 1.04], CLAMP),
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 22,
          marginBottom: 44,
          opacity: interpolate(frame, [0.35 * fps, 0.9 * fps], [0, 1], OUT),
          translate: interpolate(frame, [0.35 * fps, 1.0 * fps], ['0px 14px', '0px 0px'], OUT),
        }}
      >
        <Orb size={52} rings={false} pulse={0.015 * (1 - Math.cos((t * 2 * Math.PI) / 3))} />
        <div style={{fontSize: 32, fontWeight: 600, letterSpacing: '0.3em', color: C.accent}}>J.A.R.V.I.S.</div>
      </div>
      <Words
        text="A voice assistant"
        at={0.55 * fps}
        stagger={0.07 * fps}
        style={{fontSize: 122, fontWeight: 600, letterSpacing: '-0.04em', lineHeight: 1.08}}
      />
      <Words
        text="that actually does things."
        at={0.8 * fps}
        stagger={0.07 * fps}
        tint={(_, i) => (i > 0 ? C.accent : undefined)}
        style={{fontSize: 122, fontWeight: 600, letterSpacing: '-0.04em', lineHeight: 1.08}}
      />
      <div
        style={{
          marginTop: 52,
          fontSize: 46,
          color: C.text2,
          opacity: interpolate(frame, [1.7 * fps, 2.3 * fps], [0, 1], OUT),
          translate: interpolate(frame, [1.7 * fps, 2.4 * fps], ['0px 18px', '0px 0px'], OUT),
        }}
      >
        For Windows and Linux
      </div>
    </AbsoluteFill>
  );
};
