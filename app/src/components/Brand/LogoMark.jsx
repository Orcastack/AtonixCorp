import React from 'react';
import LedgoraLogo from '../branding/LedgoraLogo';

export const LogoMark = ({ size = 32, variant = 'white' }) => {
  return <LedgoraLogo variant={variant} size={size} withText={false} />;
};

export default LogoMark;
