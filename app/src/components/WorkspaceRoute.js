import React from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useEnterprise } from '../context/EnterpriseContext';

/**
 * WorkspaceRoute — guards workspace-scoped routes.
 * Requires authentication AND a resolvable workspace for the URL :workspaceId.
 * Also syncs activeWorkspace from the entities list if context is stale/null.
 */
const WorkspaceRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const { activeWorkspace, entities, setActiveWorkspace, fetchWorkspacePermissionSummary, getWorkspacePermissionSummary } = useEnterprise();
  const location = useLocation();
  const { workspaceId } = useParams();
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
  const [resolvedWorkspace, setResolvedWorkspace] = React.useState(null);
  const [permissionLoading, setPermissionLoading] = React.useState(true);
  const [permissionDenied, setPermissionDenied] = React.useState(false);
  const [workspaceLookupFailed, setWorkspaceLookupFailed] = React.useState(false);

  const localResolvedWorkspace = React.useMemo(() => {
    if (!workspaceId) {
      return activeWorkspace || (() => {
        try {
          const saved = localStorage.getItem('ledgora_active_workspace');
          return saved ? JSON.parse(saved) : null;
        } catch {
          return null;
        }
      })();
    }

    if (activeWorkspace && String(activeWorkspace.id) === String(workspaceId)) {
      return activeWorkspace;
    }

    const fromList = (entities || []).find((entity) => String(entity.id) === String(workspaceId)) || null;
    if (fromList) {
      return fromList;
    }

    try {
      const saved = localStorage.getItem('ledgora_active_workspace');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (String(parsed.id) === String(workspaceId)) {
          return parsed;
        }
      }
    } catch {
      return null;
    }

    return null;
  }, [activeWorkspace, entities, workspaceId]);

  const effectiveWorkspace = resolvedWorkspace || localResolvedWorkspace;
  const rawResolvedId = effectiveWorkspace?.id || workspaceId || null;
  // Only treat IDs that look like a real UUID or integer as valid workspace IDs.
  // Local/fake IDs (e.g. equity_1234567890) must not trigger API calls.
  const isValidWorkspaceId = (id) => {
    if (!id) return false;
    const s = String(id);
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s) || /^\d+$/.test(s);
  };
  const resolvedWorkspaceId = isValidWorkspaceId(rawResolvedId) ? rawResolvedId : null;
  const permissionSummary = getWorkspacePermissionSummary(resolvedWorkspaceId);
  const lookupInProgress = Boolean(workspaceId) && !effectiveWorkspace && !workspaceLookupFailed;

  React.useEffect(() => {
    let active = true;

    if (!workspaceId || effectiveWorkspace) {
      setResolvedWorkspace(null);
      return () => {
        active = false;
      };
    }

    setPermissionLoading(true);

    // Don't even attempt an API call for fake/local IDs — mark as failed immediately.
    if (!isValidWorkspaceId(workspaceId)) {
      setWorkspaceLookupFailed(true);
      setPermissionLoading(false);
      return () => { active = false; };
    }

    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    fetch(`${API_BASE_URL}/v1/workspaces/${workspaceId}`, {
      headers: token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Workspace not found');
        }
        return response.json();
      })
      .then((workspace) => {
        if (!active) return;
        setResolvedWorkspace(workspace);
        setActiveWorkspace(workspace);
        try {
          localStorage.setItem('ledgora_active_workspace', JSON.stringify(workspace));
        } catch {
          // ignore storage failures
        }
      })
      .catch(() => {
        if (!active) return;
        setResolvedWorkspace(null);
        setWorkspaceLookupFailed(true);
      })
      .finally(() => {
        if (active) {
          setPermissionLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [API_BASE_URL, effectiveWorkspace, setActiveWorkspace, workspaceId]);

  React.useEffect(() => {
    let active = true;
    setPermissionLoading(true);
    setPermissionDenied(false);

    if (!resolvedWorkspaceId || !isAuthenticated) {
      setPermissionLoading(false);
      return () => {
        active = false;
      };
    }

    fetchWorkspacePermissionSummary(resolvedWorkspaceId)
      .then((summary) => {
        if (!active) return;
        const pathParts = location.pathname.split('/').filter(Boolean);
        const workspaceIndex = pathParts.indexOf('workspace');
        const equityIndex = pathParts.indexOf('equity');

        if (workspaceIndex >= 0) {
          const section = pathParts[workspaceIndex + 2] || 'overview';
          setPermissionDenied(!summary?.workspace_sections?.[section]);
        } else if (equityIndex >= 0) {
          const section = pathParts[equityIndex + 2] || 'registry';
          setPermissionDenied(!summary?.equity_sections?.[section]);
        } else {
          setPermissionDenied(false);
        }
      })
      .catch(() => {
        if (!active) return;
        setPermissionDenied(true);
      })
      .finally(() => {
        if (active) {
          setPermissionLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [fetchWorkspacePermissionSummary, isAuthenticated, location.pathname, resolvedWorkspaceId]);

  if (loading) {
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

  if (lookupInProgress) {
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
        Loading workspace...
      </div>
    );
  }

  if (!effectiveWorkspace) {
    return <Navigate to="/app/console" state={{ from: location }} replace />;
  }

  if (permissionLoading && !permissionSummary) {
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

  if (permissionDenied) {
    return <Navigate to="/app/console" state={{ from: location }} replace />;
  }

  return children;
};

export default WorkspaceRoute;
