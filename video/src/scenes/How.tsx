import {Video} from '@remotion/media';
import {AbsoluteFill, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Backdrop, Eyebrow, Words} from '../parts';
import {C, OUT} from '../theme';
import {sceneStart} from '../timing';

// How it works: the Manim diagram (manim/how_it_works.py), drawn on black and laid over the backdrop as light.
// (The backdrop is repeated here: a blend only reaches what's inside its own fading scene.)
export const How = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill>
      <Backdrop offset={sceneStart(4) * fps} />
      <Sequence from={0.3 * fps} layout="none">
        <Video
          src={staticFile('how.mp4')}
          muted
          style={{position: 'absolute', left: 0, top: -20, width: 1920, height: 1080, mixBlendMode: 'screen'}}
        />
      </Sequence>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 104,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <Eyebrow at={0.3 * fps}>HOW IT WORKS</Eyebrow>
        <Words
          text="Nothing leaves your PC until you say the word."
          at={0.45 * fps}
          stagger={0.05 * fps}
          style={{fontSize: 76, fontWeight: 600, letterSpacing: '-0.035em'}}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 908,
          textAlign: 'center',
          fontSize: 42,
          color: C.text2,
          opacity: interpolate(frame, [4.2 * fps, 4.8 * fps], [0, 1], OUT),
          translate: interpolate(frame, [4.2 * fps, 4.9 * fps], ['0px 18px', '0px 0px'], OUT),
        }}
      >
        The wake word is found on your PC. Then one request can use every tool.
      </div>
    </AbsoluteFill>
  );
};
