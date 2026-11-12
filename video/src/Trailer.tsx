import {Audio} from '@remotion/media';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {AbsoluteFill, interpolate, staticFile, Track, useCurrentFrame, useVideoConfig} from 'remotion';
import {Backdrop} from './parts';
import {Close} from './scenes/Close';
import {Features} from './scenes/Features';
import {How} from './scenes/How';
import {Ignite} from './scenes/Ignite';
import {Title} from './scenes/Title';
import {Voice} from './scenes/Voice';
import {Window} from './scenes/Window';
import {C, CLAMP, FONT} from './theme';
import {FADE, sceneSeconds, sceneStart} from './timing';

const FadeToBlack = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        backgroundColor: 'black',
        opacity: interpolate(frame, [durationInFrames - 1.1 * fps, durationInFrames - 0.15 * fps], [0, 1], CLAMP),
      }}
    />
  );
};

// The whole trailer: seven scenes that fade into each other on the music's bar lines (timing.ts).
export const Trailer = () => {
  const {fps} = useVideoConfig();
  const cut = <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: FADE * fps})} />;
  const whoosh = staticFile('audio/whoosh.wav');
  const tick = staticFile('audio/tick.wav');
  const chime = staticFile('audio/done.wav');
  return (
    <AbsoluteFill style={{backgroundColor: C.bg, fontFamily: FONT, color: C.text}}>
      <Backdrop />
      <TransitionSeries>
        <TransitionSeries.Sequence name="Ignite" durationInFrames={sceneSeconds(0) * fps}>
          <Ignite />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="Title" durationInFrames={sceneSeconds(1) * fps}>
          <Title />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="Voice" durationInFrames={sceneSeconds(2) * fps}>
          <Voice />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="Window" durationInFrames={sceneSeconds(3) * fps}>
          <Window />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="How it works" durationInFrames={sceneSeconds(4) * fps}>
          <How />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="Features" durationInFrames={sceneSeconds(5) * fps}>
          <Features />
        </TransitionSeries.Sequence>
        {cut}
        <TransitionSeries.Sequence name="Close" durationInFrames={sceneSeconds(6) * fps}>
          <Close />
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <FadeToBlack />
      <Track name="Music">
        <Audio name="Music" src={staticFile('audio/music.wav')} volume={0.62} />
      </Track>
      <Track name="Sound effects">
        <Audio name="Reactor lights" src={staticFile('audio/ignite.wav')} from={0.2 * fps} durationInFrames={2.6 * fps} volume={0.8} />
        <Audio name="Heard" src={staticFile('audio/wake.wav')} from={3.45 * fps} durationInFrames={2.4 * fps} volume={0.5} />
        <Audio name="Notch drops" src={whoosh} from={(sceneStart(2) + 0.45) * fps} durationInFrames={0.7 * fps} volume={0.4} />
        <Audio name="Working" src={tick} from={(sceneStart(2) + 2.7) * fps} durationInFrames={0.05 * fps} volume={0.7} />
        <Audio name="Answer" src={chime} from={(sceneStart(2) + 3.9) * fps} durationInFrames={2.4 * fps} volume={0.45} />
        <Audio name="Window in" src={whoosh} from={(sceneStart(3) + 0.2) * fps} durationInFrames={0.7 * fps} volume={0.35} />
        <Audio name="Zoom" src={whoosh} from={(sceneStart(3) + 3.0) * fps} durationInFrames={0.7 * fps} volume={0.4} />
        <Audio name="Pan" src={whoosh} from={(sceneStart(3) + 6.3) * fps} durationInFrames={0.7 * fps} volume={0.4} />
        <Audio name="Wake word" src={tick} from={(sceneStart(4) + 0.95) * fps} durationInFrames={0.05 * fps} volume={0.7} />
        <Audio name="Live voice" src={tick} from={(sceneStart(4) + 2.15) * fps} durationInFrames={0.05 * fps} volume={0.7} />
        <Audio name="Agent" src={tick} from={(sceneStart(4) + 2.65) * fps} durationInFrames={0.05 * fps} volume={0.7} />
        <Audio name="Tools" src={tick} from={(sceneStart(4) + 3.15) * fps} durationInFrames={0.05 * fps} volume={0.7} />
        <Audio name="Spoken" src={chime} from={(sceneStart(4) + 5.35) * fps} durationInFrames={2.4 * fps} volume={0.4} />
        <Audio name="To memory" src={whoosh} from={(sceneStart(5) + 2.25) * fps} durationInFrames={0.7 * fps} volume={0.4} />
        <Audio name="To languages" src={whoosh} from={(sceneStart(5) + 4.65) * fps} durationInFrames={0.7 * fps} volume={0.4} />
        <Audio name="Name" src={staticFile('audio/wake.wav')} from={(sceneStart(6) + 0.5) * fps} durationInFrames={2.4 * fps} volume={0.4} />
      </Track>
    </AbsoluteFill>
  );
};
