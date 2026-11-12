import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// The app's own typeface (assets/InterVariable.ttf, SIL OFL).
loadFont({family: 'Inter Variable', url: staticFile('InterVariable.ttf'), weight: '100 900'});
