import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import { organizationsAPI } from '../../services/api';
import { countryDropdownOptionsByCode, countryDropdownOptionsByName } from '../../utils/countryDropdowns';
import './WorkspaceSelector.css';

const getCountryLabel = (country) => {
  if (!country) return 'Not Set';
  return countryDropdownOptionsByCode.get(country)?.name || countryDropdownOptionsByName.get(country)?.name || country;
};

const formatDate = (value) => {
  if (!value) return 'Not Set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

const getInitials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'LG';

const WorkspaceSelector = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { switchOrganization } = useEnterprise();
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const userLabel = user?.name || user?.email || '';
  const workspaceCount = workspaces.length;
  const pendingAccessCount = workspaces.filter((workspace) => workspace?.status === 'pending' || workspace?.invite_status === 'pending').length;

  useEffect(() => {
    let active = true;

    const loadWorkspaces = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await organizationsAPI.getMyOrganizations();
        if (!active) return;
        const items = Array.isArray(response.data) ? response.data : response.data?.results || [];
        setWorkspaces(items);
      } catch (err) {
        if (!active) return;
        setError(err.response?.data?.detail || 'Failed to load your organizations.');
        setWorkspaces([]);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadWorkspaces();

    return () => {
      active = false;
    };
  }, []);

  const handleOpenWorkspace = (org) => {
    switchOrganization(org);
    navigate('/app/enterprise/org-overview');
  };

  return (
    <div className="ws-selector-page">
      <main className="ws-selector-shell">
        <section className="ws-selector-hero">
          <div className="ws-selector-copy">
            <p className="ws-selector-kicker">Organization Selector</p>
            <h1>Choose an organization</h1>
            <p className="ws-selector-subtitle">{userLabel ? `${userLabel}, ` : ''}open the organization you want to work in.</p>

            <div className="ws-selector-summary" aria-label="Organization summary">
              <span>{workspaceCount} {workspaceCount === 1 ? 'organization' : 'organizations'} available</span>
              <strong>{pendingAccessCount} {pendingAccessCount === 1 ? 'pending access request' : 'pending access requests'}</strong>
            </div>
          </div>
        </section>

        <div className="ws-selector-actions ws-selector-actions--top">
          <button className="ws-selector-create" onClick={() => navigate('/app/organizations/create')}>
            Create Organization
          </button>
          <button className="ws-selector-secondary" onClick={() => navigate('/app/console')}>
            Back to Console
          </button>
        </div>

        {loading ? (
          <div className="ws-selector-state">Loading organizations…</div>
        ) : error ? (
          <div className="ws-selector-state ws-selector-state-error">{error}</div>
        ) : (
          <>
            {workspaces.length === 0 ? (
              <section className="ws-selector-empty">
                <div className="ws-selector-empty-copy">
                  <p className="ws-selector-kicker">No organizations yet</p>
                  <h2>Create your first organization</h2>
                  <p>Use the button above to create an organization and get started.</p>
                </div>
              </section>
            ) : (
              <section className="ws-selector-grid" aria-label="My organizations">
                {workspaces.map((workspace) => (
                    <article key={workspace.id} className="ws-selector-card">
                      <div className="ws-selector-card-top">
                        <div className="ws-selector-card-brand">
                          {workspace.logo_url ? (
                            <img className="ws-selector-card-logo" src={workspace.logo_url} alt={`${workspace.name} logo`} />
                          ) : (
                            <div className="ws-selector-card-logo ws-selector-card-logo--fallback">{getInitials(workspace.name)}</div>
                          )}
                        </div>
                        <div className="ws-selector-card-head">
                          <h2>{workspace.name}</h2>
                          <p>{workspace.description || workspace.industry || 'Organization'}</p>
                        </div>
                        <div className="ws-selector-card-badge">{formatDate(workspace.created_at)}</div>
                      </div>

                      <div className="ws-selector-card-fields">
                        <div className="ws-selector-card-field ws-selector-card-field--compact">
                          <span>Registration Number</span>
                          <strong>{workspace.registration_number || 'Verification required'}</strong>
                        </div>
                        <div className="ws-selector-card-field ws-selector-card-field--compact">
                          <span>Organization Owner</span>
                          <strong>{workspace.owner_name || workspace.owner_email || 'Owner record unavailable'}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Industry</span>
                          <strong>{workspace.industry || 'Not Set'}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Country</span>
                          <strong>{getCountryLabel(workspace.primary_country)}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Currency</span>
                          <strong>{workspace.primary_currency || 'USD'}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Employees</span>
                          <strong>{workspace.employee_count ?? 'Not Set'}</strong>
                        </div>
                        <div className="ws-selector-card-field ws-selector-card-field--compact">
                          <span>Email</span>
                          <strong>{workspace.email || workspace.owner_email || 'Not Set'}</strong>
                        </div>
                        <div className="ws-selector-card-field ws-selector-card-field--compact">
                          <span>Address</span>
                          <strong>{workspace.address || 'Not Set'}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Service Time</span>
                          <strong>{workspace.service_time || 'Not Set'}</strong>
                        </div>
                        <div className="ws-selector-card-field">
                          <span>Created</span>
                          <strong>{formatDate(workspace.created_at)}</strong>
                        </div>
                        <div className="ws-selector-card-field ws-selector-card-field--compact">
                          <span>Website</span>
                          <strong>{workspace.website || 'Not Set'}</strong>
                        </div>
                      </div>

                      <button className="ws-selector-open" onClick={() => handleOpenWorkspace(workspace)}>
                        Open Organization
                      </button>
                    </article>
                ))}
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default WorkspaceSelector;