import {Composition} from 'remotion';
import './fonts';
import {Trailer} from './Trailer';

export const RemotionRoot = () => {
  return (
    <Composition id="JarvisTrailer" component={Trailer} width={1920} height={1080} fps={60} durationInFrames={2772} />
  );
};
