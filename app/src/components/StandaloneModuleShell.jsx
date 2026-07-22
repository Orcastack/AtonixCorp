import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useEnterprise } from '../context/EnterpriseContext';
import AtonixCorpLogo from './branding/AtonixCorpLogo';
import './StandaloneModuleShell.css';

const StandaloneModuleShell = ({
  title,
  eyebrow = 'Standalone',
  backTo = '/app/console',
  backLabel = 'Back to Console',
  children,
}) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { currentOrganization, globalNotifications } = useEnterprise();
  const [profileOpen, setProfileOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(() => new Date());
  const profileRef = useRef(null);
  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="standalone-module-shell">
      <header className="standalone-console-header">
        <div className="standalone-console-header-left">
          <div className="standalone-console-brand">
            <AtonixCorpLogo variant="white" size="small" withText text="AtonixCorp" />
          </div>
          <div className="standalone-console-org-block">
            <span className="standalone-console-org-label">Organization</span>
            <strong className="standalone-console-org-name">{currentOrganization?.name || 'AtonixCorp Organization'}</strong>
          </div>
        </div>
        <div className="standalone-console-header-right" ref={profileRef}>
          <button className="standalone-console-return" onClick={() => navigate(backTo)}>{backLabel}</button>
          <div className="standalone-console-clock" aria-label="Current date and time">
            <span>{currentTime.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
            <strong>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          </div>
          <button className="standalone-console-notifications" onClick={() => navigate('/app/console')} aria-label="Open console notifications">
            <span className="standalone-console-notifications-label">Notifications</span>
            <span className="standalone-console-notifications-count">{globalNotifications?.length || 0}</span>
          </button>
          <button className="standalone-console-avatar" onClick={() => setProfileOpen((open) => !open)} aria-label="Profile menu">
            {userInitial}
          </button>
          {profileOpen && (
            <div className="standalone-console-dropdown">
              <div className="standalone-console-dropdown-header">
                <div className="standalone-console-dropdown-avatar">{userInitial}</div>
                <div>
                  <div className="standalone-console-dropdown-name">{user?.name || 'User'}</div>
                  <div className="standalone-console-dropdown-email">{user?.email || ''}</div>
                </div>
              </div>
              <div className="standalone-console-dropdown-divider" />
              <button className="standalone-console-dropdown-item" onClick={() => { setProfileOpen(false); navigate('/app/console/settings'); }}>Security</button>
              <button className="standalone-console-dropdown-item" onClick={() => { setProfileOpen(false); navigate('/app/console/settings/support-center'); }}>Help Center</button>
              <div className="standalone-console-dropdown-divider" />
              <button className="standalone-console-dropdown-item standalone-console-dropdown-logout" onClick={handleLogout}>Sign Out</button>
            </div>
          )}
        </div>
      </header>
      <div className="standalone-module-body">{children}</div>
    </div>
  );
};

export default StandaloneModuleShell;