import React from 'react';
import AtonixCorpLogo from '../branding/AtonixCorpLogo';

export const Logo = ({ height = 32 }) => {
  return <AtonixCorpLogo variant="full" size={height} withText />;
};

export default Logo;
