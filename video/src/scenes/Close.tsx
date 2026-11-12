import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Orb} from '../Orb';
import {Words} from '../parts';
import {C, OUT} from '../theme';

// The name, what to say, and where to get it.
export const Close = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <Orb
        size={250}
        spin={25.7 * t}
        pulse={0.015 * (1 - Math.cos((t * 2 * Math.PI) / 3))}
        style={{
          marginTop: 168,
          opacity: interpolate(frame, [0.2 * fps, 0.9 * fps], [0, 1], OUT),
          scale: interpolate(frame, [0.2 * fps, 1.2 * fps], [0.92, 1], OUT),
        }}
      />
      <Words
        text="J.A.R.V.I.S."
        by="letter"
        at={0.5 * fps}
        stagger={0.04 * fps}
        style={{marginTop: 62, fontSize: 132, fontWeight: 600, letterSpacing: '0.06em', lineHeight: 1.1}}
      />
      <div
        style={{
          marginTop: 24,
          fontSize: 50,
          color: C.text2,
          opacity: interpolate(frame, [1.3 * fps, 1.9 * fps], [0, 1], OUT),
          translate: interpolate(frame, [1.3 * fps, 2.0 * fps], ['0px 18px', '0px 0px'], OUT),
        }}
      >
        Say “Hey Jarvis”. It does the rest.
      </div>
      <div
        style={{
          marginTop: 64,
          padding: '22px 46px',
          borderRadius: 999,
          background: C.glass,
          border: `1px solid ${C.strokeStrong}`,
          fontSize: 42,
          fontWeight: 500,
          opacity: interpolate(frame, [1.8 * fps, 2.4 * fps], [0, 1], OUT),
          translate: interpolate(frame, [1.8 * fps, 2.5 * fps], ['0px 18px', '0px 0px'], OUT),
        }}
      >
        <span style={{color: C.text3}}>Free and open source · </span>
        github.com/Qssaf/jarvis-assistant
      </div>
    </AbsoluteFill>
  );
};
