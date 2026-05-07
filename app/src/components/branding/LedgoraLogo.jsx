import React from 'react';
import './LedgoraLogo.css';

const SIZE_MAP = {
  small: 24,
  medium: 32,
  large: 40,
};

function LedgoraLogo({ variant = 'full', withText = true, size = 'medium', text = 'Ledgora', className = '' }) {
  const dimension = typeof size === 'number' ? size : (SIZE_MAP[size] || SIZE_MAP.medium);
  const classes = ['ledgora-logo-lockup', `ledgora-logo--${variant}`, className].filter(Boolean).join(' ');
  const secondaryText = text === 'Ledgora' ? '' : text.replace('Ledgora', '').trim();

  return (
    <span className={classes}>
      {/* Square brand mark: #EE6C4D background + white shield */}
      <svg
        className="ledgora-logo-mark"
        width={dimension}
        height={dimension}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <rect width="64" height="64" rx="12" fill="#EE6C4D" />
        <path d="M32 12 L50 19 L50 34 C50 44 42 52 32 56 C22 52 14 44 14 34 L14 19 Z"
          fill="#FFFFFF" />
        <path d="M32 17 L46 23 L46 34 C46 42 40 49 32 53 C24 49 18 42 18 34 L18 23 Z"
          fill="none" stroke="#EE6C4D" strokeWidth="1.5" />
      </svg>
      {withText ? (
        <span className="ledgora-logo-wordmark">
          <span className="ledgora-logo-wordmark__primary">Ledgora</span>
          {secondaryText ? <span className="ledgora-logo-wordmark__secondary">{secondaryText}</span> : null}
        </span>
      ) : null}
    </span>
  );
}

export default LedgoraLogo;