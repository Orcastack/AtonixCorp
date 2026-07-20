import React from 'react';
import AtonixCorpLogo from '../branding/AtonixCorpLogo';
import SocialIcons from './SocialIcons';
import ComplianceBadges from './ComplianceBadges';

function FooterSecondary() {
  return (
    <div className="footer-secondary">
      <div className="footer-shell footer-secondary__inner">
        <div className="footer-secondary__identity">
          <AtonixCorpLogo variant="white" withText size="small" />
          <p className="footer-secondary__copyright">© AtonixCorp. All rights reserved.</p>
        </div>

        <div className="footer-secondary__meta">
          <SocialIcons />
          <ComplianceBadges />
        </div>
      </div>
    </div>
  );
}

export default FooterSecondary;