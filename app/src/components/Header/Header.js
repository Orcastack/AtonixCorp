import React, { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Logo } from '../Brand/Logo';
import { Icon } from '../ui';
import { FiMenu, FiX } from 'react-icons/fi';
import './Header.css';

const UTILITY_ITEMS = [
  { label: 'Contact', to: '/contact' },
  { label: 'Support', to: '/support' },
  { label: 'Security', to: '/security-center' },
  { label: 'Login', to: '/login' },
];

const NAV_ITEMS = [
  { label: 'Home',       to: '/' },
  { label: 'Services',   to: '/product' },
  { label: 'Features',   to: '/features' },
  { label: 'Global Tax', to: '/global-tax' },
  { label: 'Pricing',    to: '/pricing' },
  { label: 'About',      to: '/about' },
 // { label: 'Contact',    to: '/contact' },
];

const Header = () => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="ly-header">

      <div className="ly-utility-bar">
        <div className="ly-utility-inner">
          <nav className="ly-utility-links" aria-label="Utility navigation">
            {UTILITY_ITEMS.map(({ label, to }) => (
              <Link key={label} to={to}>
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      <div className="ly-primary-bar">
        <div className="ly-primary-inner">
          <Link to="/" className="ly-logo-link" aria-label="AtonixCorp Home">
            <Logo height={34} />
          </Link>

          <nav className="ly-primary-nav" aria-label="Primary navigation">
            {NAV_ITEMS.map(({ label, to }) => (
              <NavLink
                key={label}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  'ly-nav-link' + (isActive ? ' ly-nav-link--active' : '')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <button
            className="ly-hamburger"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileOpen}
          >
            <Icon icon={mobileOpen ? FiX : FiMenu} size="md" />
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="ly-mobile-nav" aria-label="Mobile navigation">
          {NAV_ITEMS.map(({ label, to }) => (
            <Link
              key={label}
              to={to}
              className="ly-mobile-link"
              onClick={() => setMobileOpen(false)}
            >
              {label}
            </Link>
          ))}
          <div className="ly-mobile-utility-links">
            {UTILITY_ITEMS.map(({ label, to }) => (
              <Link
                key={label}
                to={to}
                className="ly-mobile-link ly-mobile-link--utility"
                onClick={() => setMobileOpen(false)}
              >
                {label}
              </Link>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
};

export default Header;

