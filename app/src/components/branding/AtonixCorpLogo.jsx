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
      {/* Square brand mark: premium navy background + warm shield */}
      <svg
        className="atonixcorp-logo-mark"
        width={dimension}
        height={dimension}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="atonixcorp-logo-bg" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
            <stop stopColor="#081A33" />
            <stop offset="1" stopColor="#123B66" />
          </linearGradient>
          <linearGradient id="atonixcorp-logo-shield" x1="20" y1="16" x2="44" y2="52" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFFFFF" />
            <stop offset="1" stopColor="#D9E8F5" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="14" fill="url(#atonixcorp-logo-bg)" />
        <path d="M32 12 L50 19 L50 34 C50 44 42 52 32 56 C22 52 14 44 14 34 L14 19 Z"
          fill="url(#atonixcorp-logo-shield)" />
        <path d="M32 17 L46 23 L46 34 C46 42 40 49 32 53 C24 49 18 42 18 34 L18 23 Z"
          fill="none" stroke="#7DD3FC" strokeWidth="1.5" />
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