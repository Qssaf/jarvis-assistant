import {AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Words} from '../parts';
import {C, CLAMP, OUT} from '../theme';

type Props = {
  readonly n: string;
  readonly title: string;
  readonly sub: string;
  readonly page: string; // a picture in public/screens, 1280 x 820 window pixels
  readonly crop: readonly [number, number, number, number]; // the part of it to show: x, y, width, height
  readonly zoom: number;
  readonly fadeFrom?: number; // 0-1 down the picture: where a cut-off card starts fading out
  readonly leaves?: boolean;
};

// One feature: what it is, and the piece of the real window that shows it, big enough to read.
const Feature = ({n, title, sub, page, crop, zoom, fadeFrom, leaves = true}: Props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const [x, y, w, h] = crop;
  const out = leaves ? durationInFrames - 0.25 * fps : durationInFrames + 1;
  return (
    <AbsoluteFill
      style={{
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: interpolate(frame, [out, out + 0.22 * fps], [1, 0], CLAMP),
        translate: interpolate(frame, [out, out + 0.25 * fps], ['0px 0px', '0px -24px'], CLAMP),
      }}
    >
      <div
        style={{
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: '0.22em',
          color: C.accent,
          marginBottom: 20,
          opacity: interpolate(frame, [0.05 * fps, 0.5 * fps], [0, 1], OUT),
        }}
      >
        {n}
      </div>
      <Words text={title} at={0.08 * fps} stagger={0.05 * fps} style={{fontSize: 88, fontWeight: 600, letterSpacing: '-0.04em', lineHeight: 1.1}} />
      <div
        style={{
          marginTop: 18,
          fontSize: 42,
          color: C.text2,
          opacity: interpolate(frame, [0.35 * fps, 0.85 * fps], [0, 1], OUT),
          translate: interpolate(frame, [0.35 * fps, 0.95 * fps], ['0px 16px', '0px 0px'], OUT),
        }}
      >
        {sub}
      </div>
      <div
        style={{
          position: 'relative',
          marginTop: 56,
          width: w * zoom,
          height: h * zoom,
          borderRadius: 20 * zoom,
          overflow: 'hidden',
          flexShrink: 0,
          transformOrigin: '50% 0%',
          maskImage: fadeFrom === undefined ? undefined : `linear-gradient(180deg, black ${fadeFrom * 100}%, transparent 100%)`,
          boxShadow: fadeFrom === undefined ? '0 50px 120px rgba(0,0,0,0.55)' : undefined,
          opacity: interpolate(frame, [0.1 * fps, 0.6 * fps], [0, 1], OUT),
          translate: interpolate(frame, [0.1 * fps, 0.95 * fps], ['0px 70px', '0px 0px'], OUT),
          scale: interpolate(frame, [0, durationInFrames], [1, 1.025], CLAMP),
        }}
      >
        <Img
          src={staticFile(`screens/${page}.png`)}
          style={{position: 'absolute', left: -x * zoom, top: -y * zoom, width: 1280 * zoom, height: 820 * zoom, maxWidth: 'none'}}
        />
      </div>
    </AbsoluteFill>
  );
};

// Three things worth knowing, one bar of the music each.
export const Features = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill>
      <Sequence name="Accounts" durationInFrames={2.6 * fps}>
        <Feature
          n="01"
          title="Your accounts, your rules."
          sub="Ask first, full access, read only or paused. You choose, account by account."
          page="accounts"
          crop={[224, 124, 920, 329]}
          zoom={1.7}
          fadeFrom={0.78}
        />
      </Sequence>
      <Sequence name="Memory" from={2.4 * fps} durationInFrames={2.6 * fps}>
        <Feature
          n="02"
          title="It remembers what matters."
          sub="Plain notes it adds to as you talk. Edit them any time."
          page="memory"
          crop={[224, 124, 920, 232]}
          zoom={1.7}
        />
      </Sequence>
      <Sequence name="Languages" from={4.8 * fps} durationInFrames={2.8 * fps}>
        <Feature
          n="03"
          title="Speaks 19 languages."
          sub="Pick several and it answers in whichever one you speak."
          page="settings"
          crop={[348, 122, 892, 408]}
          zoom={1.5}
          fadeFrom={0.84}
          leaves={false}
        />
      </Sequence>
    </AbsoluteFill>
  );
};
