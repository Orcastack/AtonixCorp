import React, { createContext, useState, useContext, useCallback, useEffect, useMemo, useRef } from 'react';
import { useAuth } from './AuthContext';
import { workspacePermissionsAPI } from '../services/api';

const EnterpriseContext = createContext();

export const useEnterprise = () => {
  const context = useContext(EnterpriseContext);
  if (!context) {
    throw new Error('useEnterprise must be used within EnterpriseProvider');
  }
  return context;
};

export const EnterpriseProvider = ({ children }) => {
  const { user } = useAuth();
  const dashboardCacheRef = useRef(new Map());
  const dashboardInflightRef = useRef(new Map());
  const organizationPrefetchRef = useRef(new Map());

  const DASHBOARD_CACHE_TTL_MS = 60 * 1000;
  const ORG_PREFETCH_THROTTLE_MS = 15 * 1000;

  const API_BASE_URL =
    process.env.REACT_APP_API_BASE_URL ||
    (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

  const apiUrl = useCallback(
    (path) => {
      if (!path) return API_BASE_URL;
      if (path.startsWith('http://') || path.startsWith('https://')) return path;
      return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
    },
    [API_BASE_URL]
  );

  const buildAuthHeaders = useCallback(() => {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const resolveNumericEntityId = useCallback((entityId) => {
    const numericEntityId = Number(entityId);
    return Number.isInteger(numericEntityId) && String(numericEntityId) === String(entityId).trim()
      ? numericEntityId
      : null;
  }, []);

  // Silently refresh the access token using the stored refresh token.
  // Returns the new access token string, or null on failure.
  const refreshAccessToken = useCallback(async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) return null;
    try {
      const res = await fetch(apiUrl('/api/auth/token/refresh/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (data.access) {
        localStorage.setItem('token', data.access);
        if (data.refresh) localStorage.setItem('refreshToken', data.refresh);
        return data.access;
      }
      return null;
    } catch {
      return null;
    }
  }, [apiUrl]);

  // Organization state
  const [organizations, setOrganizations] = useState([]);
  const [currentOrganization, setCurrentOrganization] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Entities
  const [entities, setEntities] = useState([]);
  const [selectedEntities, setSelectedEntities] = useState([]);

  // Equity Structures
  const [equityStructures, setEquityStructures] = useState([]);

  // Active Workspace (the entity/company currently being worked on)
  const [activeWorkspace, setActiveWorkspaceState] = useState(() => {
    try {
      const saved = localStorage.getItem('ledgora_active_workspace');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Workspace-level notification/task state
  const [globalNotifications, setGlobalNotifications] = useState([]);
  const [globalTasks, setGlobalTasks] = useState([]);

  // Team
  const [teamMembers, setTeamMembers] = useState([]);
  const [currentUserRole, setCurrentUserRole] = useState(null);
  const [isRoleResolved, setIsRoleResolved] = useState(false);
  const [organizationPermissionContext, setOrganizationPermissionContext] = useState(null);
  const [workspacePermissionSummaries, setWorkspacePermissionSummaries] = useState({});

  // Permissions
  const [permissions, setPermissions] = useState([]);
  const [roles, setRoles] = useState([]);

  // Dashboard data
  const [orgOverview, setOrgOverview] = useState(null);
  const [taxExposures, setTaxExposures] = useState([]);
  const [complianceDeadlines, setComplianceDeadlines] = useState([]);
  const [cashflowData, setCashflowData] = useState([]);

  // Constants for role hierarchy
  const ROLES = useMemo(() => ({
    ORG_OWNER: 'ORG_OWNER',
    CFO: 'CFO',
    FINANCE_ANALYST: 'FINANCE_ANALYST',
    VIEWER: 'VIEWER',
    EXTERNAL_ADVISOR: 'EXTERNAL_ADVISOR',
  }), []);

  const PERMISSIONS = useMemo(() => ({
    // Org
    VIEW_ORG_OVERVIEW: 'view_org_overview',
    MANAGE_ORG_SETTINGS: 'manage_org_settings',
    MANAGE_BILLING: 'manage_billing',

    // Entity
    VIEW_ENTITIES: 'view_entities',
    CREATE_ENTITY: 'create_entity',
    EDIT_ENTITY: 'edit_entity',
    DELETE_ENTITY: 'delete_entity',

    // Tax
    VIEW_TAX_COMPLIANCE: 'view_tax_compliance',
    EDIT_TAX_COMPLIANCE: 'edit_tax_compliance',
    EXPORT_TAX_REPORTS: 'export_tax_reports',

    // Cashflow
    VIEW_CASHFLOW: 'view_cashflow',
    EDIT_CASHFLOW: 'edit_cashflow',

    // Risk
    VIEW_RISK_EXPOSURE: 'view_risk_exposure',
    EDIT_RISK_EXPOSURE: 'edit_risk_exposure',

    // Reports
    VIEW_REPORTS: 'view_reports',
    GENERATE_REPORTS: 'generate_reports',
    EXPORT_REPORTS: 'export_reports',

    // Team
    VIEW_TEAM: 'view_team',
    MANAGE_TEAM: 'manage_team',
    ASSIGN_ROLES: 'assign_roles',
  }), []);

  const getRolePermissions = useCallback((roleCode) => {
    const rolePermissionMap = {
      ORG_OWNER: Object.values(PERMISSIONS),
      CFO: Object.values(PERMISSIONS).filter(p => p !== PERMISSIONS.MANAGE_BILLING),
      FINANCE_ANALYST: [
        PERMISSIONS.VIEW_ORG_OVERVIEW,
        PERMISSIONS.VIEW_ENTITIES,
        PERMISSIONS.CREATE_ENTITY,
        PERMISSIONS.EDIT_ENTITY,
        PERMISSIONS.VIEW_TAX_COMPLIANCE,
        PERMISSIONS.EDIT_TAX_COMPLIANCE,
        PERMISSIONS.VIEW_CASHFLOW,
        PERMISSIONS.EDIT_CASHFLOW,
        PERMISSIONS.VIEW_RISK_EXPOSURE,
        PERMISSIONS.VIEW_REPORTS,
        PERMISSIONS.GENERATE_REPORTS,
      ],
      VIEWER: [
        PERMISSIONS.VIEW_ORG_OVERVIEW,
        PERMISSIONS.VIEW_ENTITIES,
        PERMISSIONS.VIEW_TAX_COMPLIANCE,
        PERMISSIONS.VIEW_CASHFLOW,
        PERMISSIONS.VIEW_RISK_EXPOSURE,
        PERMISSIONS.VIEW_REPORTS,
      ],
      EXTERNAL_ADVISOR: [
        PERMISSIONS.VIEW_TAX_COMPLIANCE,
        PERMISSIONS.VIEW_REPORTS,
      ],
    };

    return rolePermissionMap[roleCode] || [];
  }, [PERMISSIONS]);

  /**
   * Initialize enterprise data for user
   */
  useEffect(() => {
    if (user && user.account_type === 'enterprise') {
      setRoles(Object.values(ROLES));
      setCurrentUserRole(null);
      setPermissions([]);
      setIsRoleResolved(false);
      return;
    }

    setCurrentUserRole(null);
    setPermissions([]);
    setRoles([]);
    setTeamMembers([]);
    setIsRoleResolved(false);
  }, [user, ROLES]);

  useEffect(() => {
    if (!currentUserRole) {
      setPermissions([]);
      return;
    }

    if (permissions.length === 0) {
      setPermissions(getRolePermissions(currentUserRole));
    }
  }, [currentUserRole, getRolePermissions, permissions.length]);

  /**
   * Fetch organizations for current user
   */
  const fetchOrganizations = useCallback(async () => {
    if (!user) return;
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!token) {
      setOrganizations([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      let response = await fetch(apiUrl('/api/organizations/my_organizations/'), {
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        }
      });

      if (response.status === 401) {
        const newToken = await refreshAccessToken();
        if (newToken) {
          response = await fetch(apiUrl('/api/organizations/my_organizations/'), {
            headers: {
              Authorization: `Bearer ${newToken}`,
              'Content-Type': 'application/json',
            },
          });
        }
      }

      if (response.ok) {
        const data = await response.json();
        setError(null);
        setOrganizations(data);
        if (data.length > 0 && !currentOrganization) {
          setCurrentOrganization(data[0]);
        } else if (data.length === 0) {
          // No organizations — nothing to resolve permissions against, unblock the gate.
          setIsRoleResolved(true);
        }
      } else {
        setOrganizations([]);
        setIsRoleResolved(true);
        setError(response.status === 401 ? 'Your session expired. Please log in again.' : 'Failed to fetch organizations');
      }
    } catch (err) {
      setError('Failed to fetch organizations');
      console.error(err);
      setOrganizations([]);
      setIsRoleResolved(true);
    } finally {
      setLoading(false);
    }
  }, [user, currentOrganization, apiUrl, buildAuthHeaders, refreshAccessToken]);

  useEffect(() => {
    if (!user || user.account_type !== 'enterprise') return;
    fetchOrganizations();
  }, [user, fetchOrganizations]);

  /**
   * Fetch organization overview/dashboard
   */
  const fetchOrgOverview = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/organizations/${orgId}/overview/`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setOrgOverview(data);
      } else {
        setOrgOverview(null);
      }
    } catch (err) {
      console.error('Failed to fetch org overview:', err);
      setOrgOverview(null);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch entities for organization
   */
  const fetchEntities = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/entities/?organization_id=${orgId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setEntities(Array.isArray(data) ? data : data.results || []);
      } else {
        setEntities([]);
      }
    } catch (err) {
      console.error('Failed to fetch entities:', err);
      setEntities([]);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch team members
   */
  const fetchTeamMembers = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/team-members/?organization_id=${orgId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const members = Array.isArray(data) ? data : data.results || [];
        setTeamMembers(members);
      } else {
        setTeamMembers([]);
      }
    } catch (err) {
      console.error('Failed to fetch team members:', err);
      setTeamMembers([]);
    }
  }, [apiUrl, buildAuthHeaders]);

  const fetchPermissionContext = useCallback(async (orgId) => {
    if (!orgId) return null;
    setIsRoleResolved(false);
    try {
      const response = await fetch(apiUrl(`/api/organizations/${orgId}/permission_context/`), {
        headers: buildAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error('Failed to fetch permission context');
      }
      const data = await response.json();
      setOrganizationPermissionContext(data);
      setCurrentUserRole(data.role_code || null);
      setPermissions(Array.isArray(data.permission_codes) ? data.permission_codes : []);
      setIsRoleResolved(true);
      return data;
    } catch (err) {
      console.error('Failed to fetch permission context:', err);
      setOrganizationPermissionContext(null);
      setCurrentUserRole(null);
      setPermissions([]);
      setIsRoleResolved(true);
      return null;
    }
  }, [apiUrl, buildAuthHeaders]);

  const fetchWorkspacePermissionSummary = useCallback(async (workspaceId) => {
    if (!workspaceId) return null;
    const cacheKey = String(workspaceId);
    if (workspacePermissionSummaries[cacheKey]) {
      return workspacePermissionSummaries[cacheKey];
    }
    try {
      const response = await workspacePermissionsAPI.getMine(workspaceId);
      const summary = response.data;
      setWorkspacePermissionSummaries((current) => ({
        ...current,
        [cacheKey]: summary,
      }));
      return summary;
    } catch (err) {
      console.error('Failed to fetch workspace permission summary:', err);
      throw err;
    }
  }, [workspacePermissionSummaries]);

  const getWorkspacePermissionSummary = useCallback((workspaceId) => {
    if (!workspaceId) return null;
    return workspacePermissionSummaries[String(workspaceId)] || null;
  }, [workspacePermissionSummaries]);

  /**
   * Fetch tax compliance data
   */
  const fetchTaxExposures = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/tax-profiles/by_country/?organization_id=${orgId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setTaxExposures(data);
      } else {
        setTaxExposures([]);
      }
    } catch (err) {
      console.error('Failed to fetch tax exposures:', err);
      setTaxExposures([]);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch compliance deadlines
   */
  const fetchComplianceDeadlines = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/compliance-deadlines/upcoming/?organization_id=${orgId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setComplianceDeadlines(Array.isArray(data) ? data : data.results || []);
      } else {
        setComplianceDeadlines([]);
      }
    } catch (err) {
      console.error('Failed to fetch compliance deadlines:', err);
      setComplianceDeadlines([]);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch cashflow forecast
   */
  const fetchCashflowData = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      const response = await fetch(apiUrl(`/api/cashflow-forecasts/by_category/?organization_id=${orgId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setCashflowData(Array.isArray(data) ? data : data.results || []);
      } else {
        // Use empty array as fallback for cashflow (pages handle their own empty state)
        setCashflowData([]);
      }
    } catch (err) {
      console.error('Failed to fetch cashflow data, using empty array:', err);
      // Use empty array as fallback for cashflow (pages handle their own empty state)
      setCashflowData([]);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch risk & exposure dashboard data for an organization
   */
  const fetchRiskExposureDashboard = useCallback(async (orgId) => {
    if (!orgId) return null;
    try {
      const response = await fetch(apiUrl(`/api/organizations/${orgId}/risk_exposure/`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      }

      return null;
    } catch (err) {
      console.error('Failed to fetch risk exposure dashboard:', err);
      return null;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch consolidated accounting dashboard for organization with in-memory cache.
   */
  const fetchOrganizationAccountingDashboard = useCallback(async (orgId, options = {}) => {
    if (!orgId) return null;

    const { forceRefresh = false } = options;
    const cacheKey = String(orgId);
    const now = Date.now();
    const cached = dashboardCacheRef.current.get(cacheKey);

    if (!forceRefresh && cached && now - cached.timestamp < DASHBOARD_CACHE_TTL_MS) {
      return cached.data;
    }

    if (!forceRefresh && dashboardInflightRef.current.has(cacheKey)) {
      return dashboardInflightRef.current.get(cacheKey);
    }

    const requestPromise = fetch(apiUrl(`/api/organizations/${orgId}/accounting_dashboard/`), {
      headers: buildAuthHeaders(),
    })
      .then(async (response) => {
        // Auto-refresh token on 401 and retry once
        if (response.status === 401) {
          const newToken = await refreshAccessToken();
          if (!newToken) throw new Error('Session expired. Please log in again.');
          const retryResponse = await fetch(apiUrl(`/api/organizations/${orgId}/accounting_dashboard/`), {
            headers: { Authorization: `Bearer ${newToken}` },
          });
          if (!retryResponse.ok) throw new Error('Failed to fetch organization accounting dashboard');
          return retryResponse.json();
        }
        if (!response.ok) {
          throw new Error('Failed to fetch organization accounting dashboard');
        }

        const data = await response.json();
        dashboardCacheRef.current.set(cacheKey, {
          timestamp: Date.now(),
          data,
        });
        return data;
      })
      .finally(() => {
        dashboardInflightRef.current.delete(cacheKey);
      });

    dashboardInflightRef.current.set(cacheKey, requestPromise);
    return requestPromise;
  }, [apiUrl, buildAuthHeaders, DASHBOARD_CACHE_TTL_MS, refreshAccessToken]);

  /**
   * Check if current user has permission
   */
  const hasPermission = useCallback((permissionCode) => {
    if (!isRoleResolved) {
      // Roles are still loading — don't block the UI.
      // Real access control is enforced by the backend.
      return true;
    }

    return permissions.includes(permissionCode);
  }, [isRoleResolved, permissions]);

  const getDefaultDashboardPath = useCallback(() => {
    if (!user || user.account_type !== 'enterprise') {
      return '/app/console';
    }

    if (permissions.includes(PERMISSIONS.VIEW_ORG_OVERVIEW)) {
      return '/app/console';
    }

    const workspaceEntity = entities.find((entity) => entity.workspace_mode === 'workspace');
    if (workspaceEntity?.id) {
      return `/app/workspace/${workspaceEntity.id}/overview`;
    }

    const equityEntity = entities.find((entity) => entity.workspace_mode === 'equity');
    if (equityEntity?.id) {
      return `/app/equity/${equityEntity.id}/registry`;
    }

    const standardEntity = entities.find((entity) => entity.workspace_mode !== 'workspace' && entity.workspace_mode !== 'equity');
    if (standardEntity?.id) {
      return `/app/enterprise/entities/${standardEntity.id}/dashboard`;
    }

    return '/app/console';
  }, [entities, permissions, PERMISSIONS.VIEW_ORG_OVERVIEW, user]);

  /**
   * Check if user has specific role
   */
  const hasRole = useCallback((roleCode) => {
    return isRoleResolved && currentUserRole === roleCode;
  }, [currentUserRole, isRoleResolved]);

  /**
   * Switch to different organization
   */
  const switchOrganization = useCallback((org) => {
    setCurrentOrganization(org);
    const cacheKey = String(org.id);
    const now = Date.now();
    const lastPrefetchAt = organizationPrefetchRef.current.get(cacheKey) || 0;

    if (now - lastPrefetchAt < ORG_PREFETCH_THROTTLE_MS) {
      // Throttled — preserve existing role/permission state, do not clear.
      return;
    }

    // Only clear role state when actually running a fresh fetch.
    setCurrentUserRole(null);
    setPermissions([]);
    setTeamMembers([]);
    setIsRoleResolved(false);
    setOrganizationPermissionContext(null);

    organizationPrefetchRef.current.set(cacheKey, now);

    fetchPermissionContext(org.id);
    fetchOrgOverview(org.id);
    fetchEntities(org.id);
    fetchTeamMembers(org.id);
    fetchTaxExposures(org.id);
    fetchComplianceDeadlines(org.id);
    fetchCashflowData(org.id);
    fetchOrganizationAccountingDashboard(org.id).catch(() => null);
  }, [fetchPermissionContext, fetchOrgOverview, fetchEntities, fetchTeamMembers, fetchTaxExposures, fetchComplianceDeadlines, fetchCashflowData, fetchOrganizationAccountingDashboard, ORG_PREFETCH_THROTTLE_MS]);

  useEffect(() => {
    if (!currentOrganization?.id || user?.account_type !== 'enterprise') {
      return;
    }

    switchOrganization(currentOrganization);
  }, [currentOrganization, switchOrganization, user?.account_type]);

  /**
   * Create new organization
   */
  const createOrganization = useCallback(async (orgData) => {
    try {
      const response = await fetch(apiUrl('/api/organizations/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(orgData),
      });

      if (response.ok) {
        const newOrg = await response.json();
        setOrganizations([...organizations, newOrg]);
        switchOrganization(newOrg);
        return newOrg;
      } else {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || errorData?.slug?.[0] || errorData?.name?.[0] || 'Failed to create organization');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders, organizations, switchOrganization]);

  /**
   * Update organization settings
   */
  const updateOrganization = useCallback(async (orgId, updates) => {
    if (!orgId) throw new Error('Organization id is required');
    try {
      const response = await fetch(apiUrl(`/api/organizations/${orgId}/`), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(updates || {}),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to update organization');
      }

      const updatedOrg = await response.json();
      setOrganizations(prev => prev.map(o => (o.id === updatedOrg.id ? updatedOrg : o)));
      setCurrentOrganization(prev => (prev && prev.id === updatedOrg.id ? updatedOrg : prev));
      return updatedOrg;
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Delete organization when it has no remaining organization-scoped data.
   */
  const deleteOrganization = useCallback(async (orgId) => {
    if (!orgId) throw new Error('Organization id is required');

    try {
      const response = await fetch(apiUrl(`/api/organizations/${orgId}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to delete organization');
      }

      let nextCurrentOrganization = null;
      setOrganizations((prev) => {
        const nextOrganizations = prev.filter((org) => org.id !== orgId);
        nextCurrentOrganization = nextOrganizations[0] || null;
        return nextOrganizations;
      });

      setCurrentOrganization((prev) => {
        if (!prev || prev.id !== orgId) {
          return prev;
        }
        return nextCurrentOrganization;
      });

      if (nextCurrentOrganization?.id) {
        switchOrganization(nextCurrentOrganization);
      } else {
        setEntities([]);
        setTeamMembers([]);
        setOrganizationPermissionContext(null);
      }

      return true;
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders, switchOrganization]);

  /**
   * Set the active workspace (entity) and persist to localStorage.
   */
  const setActiveWorkspace = useCallback((workspace) => {
    setActiveWorkspaceState(workspace);
    if (workspace) {
      try {
        localStorage.setItem('ledgora_active_workspace', JSON.stringify(workspace));
      } catch { /* storage quota */ }
    } else {
      localStorage.removeItem('ledgora_active_workspace');
    }
  }, []);


  /**
   * Fetch global notifications — compile from compliance deadlines across all
   * accessible entities so the Global Console can show them.
   */
  const fetchGlobalNotifications = useCallback(async () => {
    if (!entities || entities.length === 0) return;
    const now = new Date();
    const notes = [];
    entities.forEach((entity) => {
      (complianceDeadlines || []).forEach((d) => {
        const daysLeft = d.deadline_date
          ? Math.ceil((new Date(d.deadline_date) - now) / (1000 * 60 * 60 * 24))
          : null;
        if (daysLeft !== null && daysLeft <= 30) {
          notes.push({
            id: `deadline-${d.id}`,
            entityId: entity.id,
            entityName: entity.name,
            type: 'tax_deadline',
            message: `${d.title} — due ${d.deadline_date}`,
            severity: daysLeft <= 0 ? 'critical' : daysLeft <= 7 ? 'high' : 'medium',
            daysLeft,
          });
        }
      });
    });
    setGlobalNotifications(notes);
  }, [entities, complianceDeadlines]);

  /**
   * Create new entity
   */
  const createEntity = useCallback(async (entityData) => {
    try {
      const response = await fetch(apiUrl('/api/entities/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(entityData),
      });

      if (response.ok) {
        const newEntity = await response.json();
        console.log('Entity created successfully:', newEntity);
        // Refresh authoritative list from server to avoid local-state drift
        try {
          if (entityData.organization_id) {
            await fetchEntities(entityData.organization_id);
          } else {
            setEntities(prev => [...prev, newEntity]);
          }
        } catch (err) {
          // fallback to local update
          setEntities(prev => [...prev, newEntity]);
        }

        return newEntity;
      } else {
        // Try to parse error response
        let errorMessage = 'Failed to create entity';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
        } catch {
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        console.error('Entity creation failed:', errorMessage);
        throw new Error(errorMessage);
      }
    } catch (err) {
      setError(err.message);
      console.error('Entity creation error:', err);
      throw err; // Re-throw so the component can handle it
    }
  }, [apiUrl, buildAuthHeaders, fetchEntities]);

  /**
   * Create a new organization record and activate its backing workspace context.
   * Also triggers default chart-of-accounts setup on the backend.
   */
  const createWorkspace = useCallback(async (workspaceData) => {
    // Convert MM-DD → YYYY-MM-DD for the API (use next upcoming occurrence)
    const rawFye = workspaceData.fiscal_year_end || workspaceData.fiscalYearEnd || '12-31';
    const toFullDate = (mmdd) => {
      const [mm, dd] = mmdd.split('-').map(Number);
      if (!mm || !dd) return mmdd; // already full date or unexpected format
      if (String(mmdd).length === 10) return mmdd; // already YYYY-MM-DD
      const now = new Date();
      const cur = now.getFullYear();
      const candidate = new Date(cur, mm - 1, dd);
      const year = candidate > now ? cur : cur + 1;
      return `${year}-${String(mm).padStart(2,'0')}-${String(dd).padStart(2,'0')}`;
    };
    const payload = {
      organization_id: workspaceData.organizationId,
      name: workspaceData.name,
      country: workspaceData.country,
      entity_type: workspaceData.businessType || 'corporation',
      local_currency: workspaceData.currency,
      fiscal_year_end: toFullDate(rawFye),
      status: 'active',
      workspace_mode: workspaceData.workspace_mode || workspaceData.workspaceMode || 'accounting',
      industry: workspaceData.industry || '',
      workspace_type: workspaceData.workspace_type || workspaceData.workspaceType || '',
      parent_entity: workspaceData.parent_entity || workspaceData.parentEntity || null,
      hierarchy_metadata: workspaceData.hierarchy_metadata || workspaceData.hierarchyMetadata || {},
      dashboard_config: workspaceData.dashboard_config || workspaceData.dashboardConfig || {},
      rbac_config: workspaceData.rbac_config || workspaceData.rbacConfig || {},
      enabled_modules: workspaceData.enabled_modules || workspaceData.enabledModules || [],
    };
    const newEntity = await createEntity(payload);
    if (newEntity) {
      setActiveWorkspace(newEntity);
    }
    return newEntity;
  }, [createEntity, setActiveWorkspace]);

  /**
   * Delete entity
   */
  const deleteEntity = useCallback(async (entityId, organizationId) => {
    if (!entityId) {
      throw new Error('Entity id is required');
    }

    try {
      const response = await fetch(apiUrl(`/api/entities/${entityId}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        let errorMessage = 'Failed to delete entity';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
        } catch {
          errorMessage = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      if (organizationId) {
        await fetchEntities(organizationId);
      } else {
        setEntities((prev) => prev.filter((entity) => entity.id !== entityId));
      }

      return true;
    } catch (err) {
      setError(err.message);
      console.error('Entity delete error:', err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders, fetchEntities]);

  /**
   * Add team member
   */
  const addTeamMember = useCallback(async (memberData) => {
    try {
      const response = await fetch('/api/team-members/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(memberData),
      });

      if (response.ok) {
        const newMember = await response.json();
        setTeamMembers([...teamMembers, newMember]);
        return newMember;
      } else {
        throw new Error('Failed to add team member');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [teamMembers]);

  /**
   * Entity-specific financial operations
   */

  /**
   * Fetch entity-specific expenses
   */
  const fetchEntityExpenses = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/expenses/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity expenses:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch entity-specific income
   */
  const fetchEntityIncome = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/income/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity income:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch entity-specific budgets
   */
  const fetchEntityBudgets = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/budgets/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity budgets:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create entity-specific expense
   */
  const createEntityExpense = useCallback(async (entityId, expenseData) => {
    try {
      const response = await fetch(apiUrl('/api/expenses/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify({ ...expenseData, entity_id: entityId }),
      });

      if (response.ok) {
        const newExpense = await response.json();
        return newExpense;
      } else {
        throw new Error('Failed to create entity expense');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create entity-specific income
   */
  const createEntityIncome = useCallback(async (entityId, incomeData) => {
    try {
      const response = await fetch(apiUrl('/api/income/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify({ ...incomeData, entity_id: entityId }),
      });

      if (response.ok) {
        const newIncome = await response.json();
        return newIncome;
      } else {
        throw new Error('Failed to create entity income');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create entity-specific budget
   */
  const createEntityBudget = useCallback(async (entityId, budgetData) => {
    try {
      const response = await fetch(apiUrl('/api/budgets/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify({ ...budgetData, entity_id: entityId }),
      });

      if (response.ok) {
        const newBudget = await response.json();
        return newBudget;
      } else {
        throw new Error('Failed to create entity budget');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [apiUrl, buildAuthHeaders]);

  // ============ Entity-Specific API Functions ============

  /**
   * Fetch entity departments
   */
  const fetchEntityDepartments = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(`/api/entity-departments/?entity=${entityId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity departments:', err);
    }
    return [];
  }, []);

  /**
   * Fetch entity roles
   */
  const fetchEntityRoles = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(`/api/entity-roles/?entity=${entityId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity roles:', err);
    }
    return [];
  }, []);

  /**
   * Fetch entity staff
   */
  const fetchEntityStaff = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(`/api/entity-staff/?entity=${entityId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity staff:', err);
    }
    return [];
  }, []);

  /**
   * Fetch entity bank accounts
   */
  const fetchEntityBankAccounts = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/bank-accounts/?entity=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity bank accounts:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch entity wallets
   */
  const fetchEntityWallets = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/wallets/?entity=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity wallets:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch entity compliance documents
   */
  const fetchEntityComplianceDocuments = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/compliance-documents/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity compliance documents:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  // ==========================================================================
  // TAX & COMPLIANCE (ENTITY-SCOPED)
  // ==========================================================================

  const fetchEntityTaxProfiles = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/tax-profiles/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity tax profiles:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  const createTaxProfile = useCallback(async (profileData) => {
    try {
      const response = await fetch(apiUrl('/api/tax-profiles/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(profileData),
      });

      if (response.ok) {
        return await response.json();
      }

      let details = 'Failed to create tax profile';
      try {
        const data = await response.json();
        details = data?.detail || JSON.stringify(data);
      } catch {
        // ignore
      }
      throw new Error(details);
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  const fetchEntityTaxExposures = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/tax-exposures/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity tax exposures:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  const fetchEntityComplianceDeadlines = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/compliance-deadlines/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity compliance deadlines:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  const createComplianceDeadline = useCallback(async (deadlineData) => {
    try {
      const response = await fetch(apiUrl('/api/compliance-deadlines/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(deadlineData),
      });
      if (response.ok) {
        return await response.json();
      }
      let details = 'Failed to create compliance deadline';
      try {
        const data = await response.json();
        details = data?.detail || JSON.stringify(data);
      } catch {
        // ignore
      }
      throw new Error(details);
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  const fetchEntityTaxCalculations = useCallback(async (entityId) => {
    if (!entityId) return [];
    try {
      const response = await fetch(apiUrl(`/api/tax-calculations/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        return Array.isArray(data) ? data : data.results || [];
      }
    } catch (err) {
      console.error('Failed to fetch entity tax calculations:', err);
    }
    return [];
  }, [apiUrl, buildAuthHeaders]);

  const calculateTax = useCallback(async (calculationPayload) => {
    try {
      const response = await fetch(apiUrl('/api/tax-calculations/calculate/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(calculationPayload),
      });

      if (response.ok) {
        return await response.json();
      }

      let details = 'Tax calculation failed';
      try {
        const data = await response.json();
        details = data?.detail || JSON.stringify(data);
      } catch {
        // ignore
      }
      throw new Error(details);
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create entity department
   */
  const createEntityDepartment = useCallback(async (departmentData) => {
    try {
      const response = await fetch('/api/entity-departments/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(departmentData),
      });

      if (response.ok) {
        const newDepartment = await response.json();
        return newDepartment;
      } else {
        throw new Error('Failed to create entity department');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, []);

  /**
   * Create entity role
   */
  const createEntityRole = useCallback(async (roleData) => {
    try {
      const response = await fetch('/api/entity-roles/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(roleData),
      });

      if (response.ok) {
        const newRole = await response.json();
        return newRole;
      } else {
        throw new Error('Failed to create entity role');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, []);

  /**
   * Create entity staff
   */
  const createEntityStaff = useCallback(async (staffData) => {
    try {
      const response = await fetch('/api/entity-staff/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(staffData),
      });

      if (response.ok) {
        const newStaff = await response.json();
        return newStaff;
      } else {
        throw new Error('Failed to create entity staff');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, []);

  /**
   * Create bank account
   */
  const createBankAccount = useCallback(async (accountData) => {
    try {
      const response = await fetch('/api/bank-accounts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(accountData),
      });

      if (response.ok) {
        const newAccount = await response.json();
        return newAccount;
      } else {
        throw new Error('Failed to create bank account');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, []);

  /**
   * Create wallet
   */
  const createWallet = useCallback(async (walletData) => {
    try {
      const response = await fetch('/api/wallets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(walletData),
      });

      if (response.ok) {
        const newWallet = await response.json();
        return newWallet;
      } else {
        throw new Error('Failed to create wallet');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, []);

  /**
   * Create compliance document
   */
  const createComplianceDocument = useCallback(async (documentData) => {
    try {
      const response = await fetch(apiUrl('/api/compliance-documents/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(documentData),
      });

      if (response.ok) {
        const newDocument = await response.json();
        return newDocument;
      } else {
        throw new Error('Failed to create compliance document');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [apiUrl, buildAuthHeaders]);

  // ============================================================================
  // BOOKKEEPING FUNCTIONS
  // ============================================================================

  /**
   * Fetch bookkeeping categories for entity
   */
  const fetchBookkeepingCategories = useCallback(async (entityId) => {
    try {
      const response = await fetch(apiUrl(`/api/bookkeeping-categories/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch categories');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return [];
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create default bookkeeping categories for entity
   */
  const createDefaultCategories = useCallback(async (entityId) => {
    try {
      const response = await fetch(apiUrl('/api/bookkeeping-categories/create_defaults/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify({ entity_id: entityId }),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to create default categories');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create custom category
   */
  const createBookkeepingCategory = useCallback(async (categoryData) => {
    try {
      const response = await fetch(apiUrl('/api/bookkeeping-categories/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(categoryData),
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create category');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch bookkeeping accounts for entity
   */
  const fetchBookkeepingAccounts = useCallback(async (entityId) => {
    try {
      const response = await fetch(apiUrl(`/api/bookkeeping-accounts/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch accounts');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return [];
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create bookkeeping account
   */
  const createBookkeepingAccount = useCallback(async (accountData) => {
    try {
      const response = await fetch(apiUrl('/api/bookkeeping-accounts/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(accountData),
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create account');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch transactions for entity with filters
   */
  const fetchTransactions = useCallback(async (entityId, filters = {}) => {
    try {
      const numericEntityId = resolveNumericEntityId(entityId);
      if (numericEntityId === null) return [];
      const params = new URLSearchParams({ entity_id: numericEntityId, ...filters });
      const response = await fetch(apiUrl(`/api/transactions/?${params}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch transactions');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return [];
    }
  }, [apiUrl, buildAuthHeaders, resolveNumericEntityId]);

  /**
   * Create transaction
   */
  const createTransaction = useCallback(async (transactionData) => {
    try {
      const response = await fetch(apiUrl('/api/transactions/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(transactionData),
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create transaction');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Update transaction
   */
  const updateTransaction = useCallback(async (transactionId, transactionData) => {
    try {
      const response = await fetch(apiUrl(`/api/transactions/${transactionId}/`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(transactionData),
      });

      if (response.ok) {
        return await response.json();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update transaction');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Delete transaction
   */
  const deleteTransaction = useCallback(async (transactionId) => {
    try {
      const response = await fetch(apiUrl(`/api/transactions/${transactionId}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return true;
      } else {
        throw new Error('Failed to delete transaction');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch bookkeeping summary for entity
   */
  const fetchBookkeepingSummary = useCallback(async (entityId, filters = {}) => {
    try {
      const numericEntityId = resolveNumericEntityId(entityId);
      if (numericEntityId === null) return null;
      const params = new URLSearchParams({ entity_id: numericEntityId, ...filters });
      const response = await fetch(apiUrl(`/api/transactions/summary/?${params}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch summary');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return null;
    }
  }, [apiUrl, buildAuthHeaders, resolveNumericEntityId]);

  /**
   * Fetch cashflow treasury dashboard data
   */
  const fetchCashflowTreasuryDashboard = useCallback(async (entityId, filters = {}) => {
    try {
      const numericEntityId = resolveNumericEntityId(entityId);
      if (numericEntityId === null) return null;
      const params = new URLSearchParams({ entity_id: numericEntityId, ...filters });
      const response = await fetch(apiUrl(`/api/cashflow-treasury/dashboard/?${params}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch cashflow treasury data');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return null;
    }
  }, [apiUrl, buildAuthHeaders, resolveNumericEntityId]);

  /**
   * Execute internal transfer
   */
  const executeInternalTransfer = useCallback(async (transferData) => {
    try {
      const response = await fetch(apiUrl('/api/cashflow-treasury/transfer/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(transferData),
      });

      const data = await response.json();
      if (response.ok) {
        return data;
      }
      throw new Error(data?.error || 'Failed to execute transfer');
    } catch (err) {
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Execute FX conversion
   */
  const executeFXConversion = useCallback(async (conversionData) => {
    try {
      const response = await fetch(apiUrl('/api/cashflow-treasury/fx_conversion/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(conversionData),
      });

      const data = await response.json();
      if (response.ok) {
        return data;
      }
      throw new Error(data?.error || 'Failed to execute FX conversion');
    } catch (err) {
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Execute investment allocation
   */
  const executeInvestmentAllocation = useCallback(async (allocationData) => {
    try {
      const response = await fetch(apiUrl('/api/cashflow-treasury/investment_allocation/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...buildAuthHeaders(),
        },
        body: JSON.stringify(allocationData),
      });

      const data = await response.json();
      if (response.ok) {
        return data;
      }
      throw new Error(data?.error || 'Failed to execute investment allocation');
    } catch (err) {
      throw err;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Fetch audit logs for entity
   */
  const fetchBookkeepingAuditLogs = useCallback(async (entityId) => {
    try {
      const response = await fetch(apiUrl(`/api/bookkeeping-audit-logs/?entity_id=${entityId}`), {
        headers: buildAuthHeaders(),
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Failed to fetch audit logs');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
      return null;
    }
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Create an equity structure (cap table, share class, vesting plan, etc.)
   */
  const createEquityStructure = useCallback(async (equityData) => {
    try {
      // Store locally — API endpoint to be wired when backend is ready
      const newStructure = {
        id: `equity_${Date.now()}`,
        created_at: new Date().toISOString(),
        status: 'active',
        ...equityData,
      };
      setEquityStructures((prev) => [...prev, newStructure]);
      return newStructure;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  const value = {
    // State
    organizations,
    currentOrganization,
    entities,
    equityStructures,
    selectedEntities,
    teamMembers,
    currentUserRole,
    isRoleResolved,
    permissions,
    organizationPermissionContext,
    roles,
    orgOverview,
    taxExposures,
    complianceDeadlines,
    cashflowData,
    loading,
    error,

    // Constants
    ROLES,
    PERMISSIONS,

    // Methods
    fetchOrganizations,
    fetchOrgOverview,
    fetchEntities,
    fetchTeamMembers,
    fetchPermissionContext,
    fetchTaxExposures,
    fetchComplianceDeadlines,
    fetchCashflowData,
    fetchOrganizationAccountingDashboard,
    fetchRiskExposureDashboard,
    hasPermission,
    hasRole,
    fetchWorkspacePermissionSummary,
    getWorkspacePermissionSummary,
    getDefaultDashboardPath,
    switchOrganization,
    createOrganization,
    updateOrganization,
    deleteOrganization,
    createEntity,
    deleteEntity,
    addTeamMember,

    // Entity-specific financial methods
    fetchEntityExpenses,
    fetchEntityIncome,
    fetchEntityBudgets,
    createEntityExpense,
    createEntityIncome,
    createEntityBudget,

    // Entity-specific management methods
    fetchEntityDepartments,
    fetchEntityRoles,
    fetchEntityStaff,
    fetchEntityBankAccounts,
    fetchEntityWallets,
    fetchEntityComplianceDocuments,
    fetchEntityTaxProfiles,
    createTaxProfile,
    fetchEntityTaxExposures,
    fetchEntityComplianceDeadlines,
    createComplianceDeadline,
    fetchEntityTaxCalculations,
    calculateTax,
    createEntityDepartment,
    createEntityRole,
    createEntityStaff,
    createBankAccount,
    createWallet,
    createComplianceDocument,

    // Bookkeeping functions
    fetchBookkeepingCategories,
    createDefaultCategories,
    createBookkeepingCategory,
    fetchBookkeepingAccounts,
    createBookkeepingAccount,
    fetchTransactions,
    createTransaction,
    updateTransaction,
    deleteTransaction,
    fetchBookkeepingSummary,
    fetchBookkeepingAuditLogs,
    fetchCashflowTreasuryDashboard,
    executeInternalTransfer,
    executeFXConversion,
    executeInvestmentAllocation,

    // Workspace
    activeWorkspace,
    setActiveWorkspace,
    createWorkspace,

    // Equity
    createEquityStructure,

    globalNotifications,
    globalTasks,
    setGlobalTasks,
    fetchGlobalNotifications,

    // Setters
    setCurrentOrganization,
    setSelectedEntities,
    setError,
  };

  return (
    <EnterpriseContext.Provider value={value}>
      {children}
    </EnterpriseContext.Provider>
  );
};

export default EnterpriseContext;
