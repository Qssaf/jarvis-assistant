import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption, Eyebrow, Words} from '../parts';
import {C, CLAMP, IN_OUT, OUT, rgba} from '../theme';

// seconds into the scene: the whole window, then in on the conversation, then across to the jobs
const ZOOM = 3.0;
const PAN = 6.3;
const MOVE = 1.0;

// A soft outline around one thing in the window (window pixels: the picture is 1280 x 820).
const Ring = ({
  x,
  y,
  w,
  h,
  r,
  from,
  to,
  color,
}: {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly r: number;
  readonly from: number;
  readonly to: number;
  readonly color: string;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        left: x - 4,
        top: y - 4,
        width: w + 8,
        height: h + 8,
        borderRadius: r + 4,
        border: `1.5px solid ${color}`,
        boxShadow: `0 0 22px ${rgba(color, 0.45)}, inset 0 0 14px ${rgba(color, 0.18)}`,
        opacity: interpolate(frame, [from, from + 0.35 * fps, to - 0.25 * fps, to], [0, 1, 1, 0], CLAMP),
        scale: interpolate(frame, [from, from + 0.5 * fps], [1.06, 1], OUT),
      }}
    />
  );
};

// The real window (docs/screens.py, made-up data): what a day with Jarvis looks like.
export const Window = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const zoom = ZOOM * fps;
  const pan = PAN * fps;
  const move = MOVE * fps;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{scale: interpolate(frame, [0, durationInFrames], [1, 1.035], CLAMP)}}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1280,
            height: 820,
            transformOrigin: '0 0',
            translate: interpolate(
              frame,
              [zoom, zoom + move, pan, pan + move],
              ['346px 218px', '-130px -120px', '-130px -120px', '-720px -400px'],
              IN_OUT,
            ),
            scale: interpolate(frame, [zoom, zoom + move], [0.96, 2], IN_OUT),
          }}
        >
          <div
            style={{
              width: 1280,
              height: 820,
              borderRadius: 22,
              boxShadow: `0 50px 130px rgba(0,0,0,0.65), 0 0 160px ${rgba(C.accent, 0.07)}`,
              transformOrigin: '50% 100%',
              opacity: interpolate(frame, [0.2 * fps, 0.8 * fps], [0, 1], OUT),
              transform: `perspective(2400px) rotateX(${interpolate(frame, [0.2 * fps, 1.4 * fps], [14, 0], OUT)}deg) translateY(${interpolate(frame, [0.2 * fps, 1.4 * fps], [130, 0], OUT)}px) scale(${interpolate(frame, [0.2 * fps, 1.4 * fps], [0.94, 1], OUT)})`,
            }}
          >
            <Img src={staticFile('screens/home.png')} style={{width: 1280, height: 820, display: 'block'}} />
            <Ring x={180} y={171} w={170} h={28} r={14} from={zoom + move} to={pan} color={C.warm} />
            <Ring x={968} y={356} w={300} h={168} r={20} from={pan + move} to={durationInFrames - 0.3 * fps} color={C.accent} />
          </div>
        </div>
      </AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 54,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 12,
          opacity: interpolate(frame, [zoom - 0.25 * fps, zoom + 0.1 * fps], [1, 0], CLAMP),
          translate: interpolate(frame, [zoom - 0.25 * fps, zoom + 0.3 * fps], ['0px 0px', '0px -30px'], IN_OUT),
        }}
      >
        <Eyebrow at={0.4 * fps}>IT DOES THE WORK</Eyebrow>
        <Words
          text="Ask once. It handles the rest."
          at={0.55 * fps}
          stagger={0.06 * fps}
          style={{fontSize: 78, fontWeight: 600, letterSpacing: '-0.035em'}}
        />
      </div>
      <AbsoluteFill
        style={{
          background: 'linear-gradient(180deg, rgba(5,8,13,0) 60%, rgba(5,8,13,0.95) 90%)',
          opacity: interpolate(frame, [zoom + 0.4 * fps, zoom + move + 0.2 * fps], [0, 1], CLAMP),
        }}
      />
      <Caption from={zoom + move} to={pan + 0.2 * fps} dot={C.warm}>
        It searches, reads your accounts and drives your apps
      </Caption>
      <Caption from={pan + move} to={durationInFrames}>
        Long jobs run in the background while you keep talking
      </Caption>
    </AbsoluteFill>
  );
};
