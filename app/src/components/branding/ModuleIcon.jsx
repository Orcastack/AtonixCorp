import React from 'react';

const iconPaths = {
  workspace: (
    <>
      <path d="M4 7.5h6l1.5 2H20v9.5H4z" />
      <path d="M4 9.5h16" />
    </>
  ),
  governance: (
    <>
      <path d="M12 3.5 20 7v5.5c0 4.5-3.2 7.3-8 8.5-4.8-1.2-8-4-8-8.5V7z" />
      <path d="M8.5 12h7M12 8.5v7" />
    </>
  ),
  security: (
    <>
      <path d="M12 3.5 20 7v5.5c0 4.5-3.2 7.3-8 8.5-4.8-1.2-8-4-8-8.5V7z" />
      <path d="M9.5 12 11.25 13.75 15 10" />
    </>
  ),
  compute: (
    <>
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M9 2.5v3M15 2.5v3M9 18.5v3M15 18.5v3M2.5 9h3M18.5 9h3M2.5 15h3M18.5 15h3M9.5 9.5h5v5h-5z" />
    </>
  ),
};

function ModuleIcon({ name, size = 18, label }) {
  const paths = iconPaths[name];

  if (!paths) {
    return null;
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? 'img' : undefined}
      focusable="false"
    >
      {paths}
    </svg>
  );
}

export default ModuleIcon;