import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import { organizationsAPI } from '../../services/api';
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi';
import { countryDropdownOptionsByCode, countryDropdownOptionsByName } from '../../utils/countryDropdowns';
import organizationCardFields from './organizationCardFields.json';
import './WorkspaceSelector.css';

const ORGANIZATIONS_PER_PAGE = 4;

const getCountryLabel = (country) => {
  if (!country) return 'Not Set';
  return countryDropdownOptionsByCode.get(country)?.name || countryDropdownOptionsByName.get(country)?.name || country;
};

const getInitials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'LG';

const getCardValue = (workspace, field) => {
  if (field.key === 'primary_country') return getCountryLabel(workspace.primary_country);
  if (field.key === 'email') return workspace.email || workspace.owner_email || field.fallback;
  if (field.key === 'owner_name') return workspace.owner_name || workspace.owner_email || field.fallback;
  return workspace[field.key] ?? field.fallback;
};

const WorkspaceSelector = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { switchOrganization } = useEnterprise();
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const userLabel = user?.name || user?.email || '';
  const workspaceCount = workspaces.length;
  const pendingAccessCount = workspaces.filter((workspace) => workspace?.status === 'pending' || workspace?.invite_status === 'pending').length;
  const pageCount = Math.max(1, Math.ceil(workspaceCount / ORGANIZATIONS_PER_PAGE));
  const visibleWorkspaces = workspaces.slice(
    currentPage * ORGANIZATIONS_PER_PAGE,
    (currentPage + 1) * ORGANIZATIONS_PER_PAGE,
  );

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, pageCount - 1));
  }, [pageCount]);

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

  const handleEditWorkspace = (org) => {
    switchOrganization(org);
    navigate('/app/enterprise/settings');
  };

  const handleManageWorkspace = (org) => {
    switchOrganization(org);
    navigate('/app/enterprise/team');
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
              <section className="ws-selector-collection" aria-label="My organizations">
                <div className="ws-selector-collection-head">
                  <div>
                    <h2>Organizations</h2>
                    <p>Page {currentPage + 1} of {pageCount}</p>
                  </div>
                  {pageCount > 1 && (
                    <div className="ws-selector-pagination" aria-label="Organization pages">
                      <button
                        type="button"
                        className="ws-selector-page-button"
                        onClick={() => setCurrentPage((page) => Math.max(0, page - 1))}
                        disabled={currentPage === 0}
                        aria-label="Previous organization page"
                        title="Previous organizations"
                      >
                        <FiChevronLeft aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        className="ws-selector-page-button"
                        onClick={() => setCurrentPage((page) => Math.min(pageCount - 1, page + 1))}
                        disabled={currentPage === pageCount - 1}
                        aria-label="Next organization page"
                        title="Next organizations"
                      >
                        <FiChevronRight aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </div>
                <div className="ws-selector-rail">
                  {visibleWorkspaces.map((workspace) => (
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
                        <div className="ws-selector-card-badge">Active</div>
                      </div>

                      <div className="ws-selector-card-fields">
                        {organizationCardFields.map((field) => (
                          <div key={field.key} className="ws-selector-card-field">
                            <span>{field.label}</span>
                            <strong>{getCardValue(workspace, field)}</strong>
                          </div>
                        ))}
                      </div>

                      <div className="ws-selector-card-actions">
                        <button className="ws-selector-open" onClick={() => handleOpenWorkspace(workspace)}>Open</button>
                        <button className="ws-selector-card-action" onClick={() => handleEditWorkspace(workspace)}>Edit</button>
                        <button className="ws-selector-card-action" onClick={() => handleManageWorkspace(workspace)}>Manage</button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default WorkspaceSelector;