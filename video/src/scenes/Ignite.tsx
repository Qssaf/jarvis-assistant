import {AbsoluteFill, interpolate, interpolateColors, useCurrentFrame, useVideoConfig} from 'remotion';
import {Orb} from '../Orb';
import {Words} from '../parts';
import {C, CLAMP, IN_OUT, OUT} from '../theme';

// The reactor lights up in the dark, then hears "Hey Jarvis".
export const Ignite = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const lit = 1.7 * fps; // the core catches (the ring in audio/ignite.wav)
  const heard = 3.45 * fps;
  // the two words, as the reactor hears them
  const voice = Math.exp(-(((t - 2.9) / 0.13) ** 2)) + 0.8 * Math.exp(-(((t - 3.2) / 0.16) ** 2));
  const pulse =
    0.015 * (1 - Math.cos((t * 2 * Math.PI) / 3)) +
    interpolate(frame, [lit, lit + 0.12 * fps, lit + 1.1 * fps], [0, 0.2, 0], CLAMP) +
    voice * 0.1;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 960 - 220,
          top: 540 - 220,
          translate: interpolate(frame, [2.3 * fps, 3.1 * fps], ['0px 0px', '0px -120px'], IN_OUT),
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `2px solid ${C.accent}`,
            opacity: interpolate(frame, [lit, lit + 1.0 * fps], [0.55, 0], OUT),
            scale: interpolate(frame, [lit, lit + 1.0 * fps], [0.5, 2.1], OUT),
          }}
        />
        <Orb
          size={440}
          tint={interpolateColors(frame, [heard, heard + 0.4 * fps], [C.accent, C.listen])}
          spin={25.7 * t + 240 * (1 - Math.exp(-t / 0.9)) + 46 * Math.max(0, t - 3.45)}
          pulse={pulse}
          draw={interpolate(frame, [0.4 * fps, 1.7 * fps], [0, 1], IN_OUT)}
          power={interpolate(frame, [lit, lit + 0.3 * fps], [0, 1], OUT)}
        />
      </div>
      <Words
        text="“Hey Jarvis”"
        at={2.75 * fps}
        stagger={0.26 * fps}
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 678,
          textAlign: 'center',
          fontSize: 132,
          fontWeight: 600,
          letterSpacing: '-0.035em',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 872,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 18,
          fontSize: 40,
          fontWeight: 500,
          color: C.text2,
          opacity: interpolate(frame, [heard, heard + 0.4 * fps], [0, 1], OUT),
          translate: interpolate(frame, [heard, heard + 0.6 * fps], ['0px 16px', '0px 0px'], OUT),
        }}
      >
        <div
          style={{
            width: 16,
            height: 16,
            borderRadius: 8,
            background: C.listen,
            boxShadow: `0 0 20px ${C.listen}`,
            opacity: 0.6 + 0.4 * Math.sin(t * 6),
          }}
        />
        Listening
      </div>
    </AbsoluteFill>
  );
};
