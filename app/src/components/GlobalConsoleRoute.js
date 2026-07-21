import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useEnterprise } from '../context/EnterpriseContext';

const GlobalConsoleRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();
  const { organizations, getDefaultDashboardPath, hasPermission, loading: enterpriseLoading } = useEnterprise();
  const location = useLocation();

  if (loading || enterpriseLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-base)',
        color: 'var(--color-silver-dark)',
        background: 'var(--color-silver-very-light)',
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!user?.email_verified) {
    return <Navigate to="/verify-email" replace />;
  }

  if (organizations.length === 0) {
    return <Navigate to="/app/organizations/create" state={{ from: location }} replace />;
  }

  if (!hasPermission('view_org_overview')) {
    const fallbackPath = getDefaultDashboardPath();

    if (fallbackPath !== location.pathname) {
      return <Navigate to={fallbackPath} state={{ from: location }} replace />;
    }

    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '60vh',
        fontFamily: 'var(--font-family)',
        gap: '12px',
      }}>
        <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, color: 'var(--color-midnight)' }}>
          Access Restricted
        </div>
        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-silver-dark)' }}>
          No dashboard is available for your current permissions.
        </div>
      </div>
    );
  }

  return children;
};

export default GlobalConsoleRoute;