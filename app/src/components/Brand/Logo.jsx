import React from 'react';
import LedgoraLogo from '../branding/LedgoraLogo';

export const Logo = ({ height = 32 }) => {
  return <LedgoraLogo variant="full" size={height} withText />;
};

export default Logo;
