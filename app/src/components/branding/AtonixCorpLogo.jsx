import React from 'react';
import './AtonixCorpLogo.css';

const SIZE_MAP = {
  small: 24,
  medium: 32,
  large: 40,
};

function AtonixCorpLogo({ variant = 'full', withText = true, size = 'medium', text = 'AtonixCorp', className = '' }) {
  const dimension = typeof size === 'number' ? size : (SIZE_MAP[size] || SIZE_MAP.medium);
  const classes = ['atonixcorp-logo-lockup', `atonixcorp-logo--${variant}`, className].filter(Boolean).join(' ');
  const secondaryText = text === 'AtonixCorp' ? '' : text.replace('AtonixCorp', '').trim();

  return (
    <span className={classes}>
      <svg
        className="atonixcorp-logo-mark"
        width={dimension}
        height={dimension}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <rect width="64" height="64" rx="14" fill="#0B1F3A" />
        <path d="M32 12 L50 19 L50 34 C50 44 42 52 32 56 C22 52 14 44 14 34 L14 19 Z"
          fill="#FFFFFF" />
        <path d="M24 28h7m2 0h7M31 28v8m0 0h7" fill="none" stroke="#1F9D91" strokeWidth="2" strokeLinecap="round" />
        <circle cx="22" cy="28" r="2.5" fill="#1F9D91" />
        <circle cx="40" cy="28" r="2.5" fill="#1F9D91" />
        <circle cx="31" cy="38" r="2.5" fill="#1F9D91" />
        <circle cx="40" cy="38" r="2.5" fill="#1F9D91" />
      </svg>
      {withText ? (
        <span className="atonixcorp-logo-wordmark">
          <span className="atonixcorp-logo-wordmark__primary">AtonixCorp</span>
          {secondaryText ? <span className="atonixcorp-logo-wordmark__secondary">{secondaryText}</span> : null}
        </span>
      ) : null}
    </span>
  );
}

export default AtonixCorpLogo;