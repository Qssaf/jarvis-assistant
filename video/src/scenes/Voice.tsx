import {AbsoluteFill, interpolate, interpolateColors, useCurrentFrame, useVideoConfig} from 'remotion';
import {Orb} from '../Orb';
import {Words} from '../parts';
import {C, CLAMP, DRAWER, IN_OUT, OUT, rgba} from '../theme';

// seconds into the scene
const DROP = 0.45; // the notch comes down
const ASK = 0.95; // the user starts talking
const WORK = 2.7; // Jarvis starts on it
const SPEAK = 3.9; // and answers, 1.2 s later

const talking = (t: number) => Math.abs(Math.sin(t * 9) * Math.sin(t * 2.3));

const Bars = ({level, color}: {readonly level: number; readonly color: string}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 6, height: 40, marginLeft: 20}}>
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          style={{
            width: 6,
            borderRadius: 3,
            background: color,
            height: 8 + 30 * level * (0.35 + 0.65 * Math.abs(Math.sin(t * (7 + i * 1.7) + i * 1.3))),
          }}
        />
      ))}
    </div>
  );
};

// The notch that hangs from the top of the screen (jarvis.py's Notch), at video size.
const Notch = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const work = WORK * fps;
  const speak = SPEAK * fps;
  const width = interpolate(frame, [work, work + 0.5 * fps, speak, speak + 0.5 * fps], [520, 800, 800, 520], DRAWER);
  const tint = interpolateColors(frame, [work, work + 0.3 * fps, speak, speak + 0.3 * fps], [C.listen, C.warm, C.warm, C.listen]);
  const heard = t > ASK && t < WORK - 0.25 ? 0.25 + 0.75 * talking(t) : 0.08;
  const said = t > SPEAK + 0.15 ? 0.25 + 0.75 * talking(t) : 0.08;
  const pulse = t < WORK ? 0.02 + heard * 0.12 : t < SPEAK ? 0.015 + 0.015 * Math.sin(t * 4) : 0.03 + 0.05 * talking(t);
  const label = {fontSize: 22, fontWeight: 600, letterSpacing: '0.14em', color: tint} as const;
  const row = {position: 'absolute', left: 104, top: 0, height: 96, display: 'flex', alignItems: 'center', whiteSpace: 'nowrap'} as const;
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 960 - width / 2,
        width,
        height: 96,
        borderRadius: '0 0 44px 44px',
        background: 'rgba(4,10,16,0.96)',
        border: `1px solid ${rgba(C.accent, 0.2)}`,
        borderTop: 'none',
        boxShadow: '0 26px 80px rgba(0,0,0,0.6)',
        overflow: 'hidden',
        translate: interpolate(frame, [DROP * fps, (DROP + 0.55) * fps], ['0px -112px', '0px 0px'], DRAWER),
      }}
    >
      <Orb size={60} rings={false} tint={tint} pulse={pulse} style={{position: 'absolute', left: 22, top: 18}} />
      <div style={{...row, opacity: interpolate(frame, [work, work + 0.15 * fps], [1, 0], CLAMP)}}>
        <span style={label}>LISTENING</span>
        <Bars level={heard} color={C.listen} />
      </div>
      <div
        style={{
          ...row,
          opacity: interpolate(frame, [work + 0.15 * fps, work + 0.4 * fps, speak, speak + 0.15 * fps], [0, 1, 1, 0], CLAMP),
        }}
      >
        <span style={label}>WORKING</span>
        <span style={{fontSize: 31, fontWeight: 500, marginLeft: 20}}>Checking Classroom</span>
      </div>
      <div style={{...row, opacity: interpolate(frame, [speak + 0.15 * fps, speak + 0.4 * fps], [0, 1], CLAMP)}}>
        <span style={label}>SPEAKING</span>
        <Bars level={said} color={C.listen} />
      </div>
      <div
        style={{
          position: 'absolute',
          right: 86,
          top: 22,
          width: 52,
          height: 52,
          borderRadius: 26,
          background: 'rgba(255,255,255,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 7,
        }}
      >
        <div style={{width: 7, height: 20, background: 'white', borderRadius: 1}} />
        <div style={{width: 7, height: 20, background: 'white', borderRadius: 1}} />
      </div>
      <div
        style={{
          position: 'absolute',
          right: 22,
          top: 22,
          width: 52,
          height: 52,
          borderRadius: 26,
          background: C.red,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{width: 18, height: 18, background: 'white', borderRadius: 4}} />
      </div>
    </div>
  );
};

// One request, start to finish: you ask, the notch shows it working, it answers out loud.
export const Voice = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const work = WORK * fps;
  const speak = SPEAK * fps;
  return (
    <AbsoluteFill>
      <Notch />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 392,
          textAlign: 'center',
          opacity: interpolate(frame, [work, work + 0.6 * fps], [1, 0.5], IN_OUT),
          scale: interpolate(frame, [work, work + 0.7 * fps], [1, 0.5], IN_OUT),
          translate: interpolate(frame, [work, work + 0.7 * fps], ['0px 0px', '0px -150px'], IN_OUT),
        }}
      >
        <Words
          text="“What’s due this week?”"
          at={ASK * fps}
          stagger={0.13 * fps}
          style={{fontSize: 108, fontWeight: 600, letterSpacing: '-0.035em'}}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 468,
          display: 'flex',
          justifyContent: 'center',
          opacity: interpolate(frame, [work + 0.25 * fps, work + 0.6 * fps, speak - 0.05 * fps, speak + 0.2 * fps], [0, 1, 1, 0], CLAMP),
          translate: interpolate(frame, [work + 0.25 * fps, work + 0.8 * fps, speak, speak + 0.3 * fps], ['0px 18px', '0px 0px', '0px 0px', '0px -14px'], OUT),
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            padding: '18px 38px 18px 30px',
            borderRadius: 999,
            background: C.glass,
            border: `1px solid ${C.strokeStrong}`,
            fontSize: 42,
            fontWeight: 500,
            color: C.text2,
          }}
        >
          <div style={{width: 16, height: 16, borderRadius: 8, background: C.warm, boxShadow: `0 0 18px ${C.warm}`}} />
          Checking Classroom
        </div>
      </div>
      <Words
        text="Two things: the Calculus problem set on Wednesday, and the History essay draft on Friday."
        at={speak + 0.15 * fps}
        stagger={0.085 * fps}
        rise={18}
        style={{
          position: 'absolute',
          left: 250,
          width: 1420,
          top: 452,
          textAlign: 'center',
          fontSize: 68,
          fontWeight: 500,
          letterSpacing: '-0.025em',
          lineHeight: 1.3,
          whiteSpace: 'normal',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 884,
          textAlign: 'center',
          fontSize: 44,
          color: C.text2,
          opacity: interpolate(frame, [5.5 * fps, 6.0 * fps], [0, 1], OUT),
          translate: interpolate(frame, [5.5 * fps, 6.2 * fps], ['0px 18px', '0px 0px'], OUT),
        }}
      >
        Real-time voice. It answers in about a second and a half.
      </div>
    </AbsoluteFill>
  );
};
