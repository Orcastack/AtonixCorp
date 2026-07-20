import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import { countries, getBanksByCountryCode } from '../../utils/countries';
import { countryDropdownOptions, countryDropdownOptionsByName } from '../../utils/countryDropdowns';
import './EnterpriseActionPages.css';
import '../../styles/EntityPages.css';

const EnterpriseEntities = () => {
  const navigate = useNavigate();
  const {
    currentOrganization,
    entities,
    fetchEntities,
    createEntity,
    deleteEntity,
    hasPermission,
    PERMISSIONS,
    loading,
    error
  } = useEnterprise();

  const [showModal, setShowModal] = useState(false);
  const [editingEntity, setEditingEntity] = useState(null);
  const [deletingEntityId, setDeletingEntityId] = useState(null);
  const [availableBanks, setAvailableBanks] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    country: '',
    entity_type: 'corporation',
    status: 'active',
    registration_number: '',
    local_currency: 'USD',
    main_bank: '',
    fiscal_year_end: '',
    next_filing_date: '',
  });

  useEffect(() => {
    if (currentOrganization) {
      fetchEntities(currentOrganization.id);
    }
  }, [currentOrganization, fetchEntities]);

  useEffect(() => {
    const loadWorkspaces = async () => {
      if (!currentOrganization?.id) {
        setWorkspaces([]);
        return;
      }

      try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        const response = await fetch(`/api/organizations/${currentOrganization.id}/workspaces/`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          setWorkspaces([]);
          return;
        }

        const data = await response.json();
        setWorkspaces(Array.isArray(data.results) ? data.results : []);
      } catch (err) {
        console.error('Failed to fetch workspaces:', err);
        setWorkspaces([]);
      }
    };

    loadWorkspaces();
  }, [currentOrganization]);

  const workspaceByEntityId = useMemo(() => {
    return workspaces.reduce((accumulator, workspace) => {
      if (workspace?.linked_entity_id) {
        accumulator[String(workspace.linked_entity_id)] = workspace;
      }
      return accumulator;
    }, {});
  }, [workspaces]);

  if (!hasPermission(PERMISSIONS.VIEW_ENTITIES)) {
    return <div className="permission-denied">You don't have permission to view entities.</div>;
  }

  const handleOpenModal = (entity = null) => {
    if (entity) {
      setFormData(entity);
      setEditingEntity(entity.id);
      // Set available banks for existing entity
      const banks = getBanksByCountryCode(entity.country);
      setAvailableBanks(banks);
    } else {
      setFormData({
        name: '',
        country: '',
        entity_type: 'corporation',
        status: 'active',
        registration_number: '',
        local_currency: 'USD',
        main_bank: '',
        fiscal_year_end: '',
        next_filing_date: '',
      });
      setEditingEntity(null);
      setAvailableBanks([]);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingEntity(null);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;

    // Auto-populate currency and banks when country is selected
    if (name === 'country' && value) {
      const selectedCountry = countryDropdownOptionsByName.get(value) || countries.find(country => country.name === value);
      if (selectedCountry) {
        // Extract currency code from currency object
        const currencyCode = selectedCountry.currency?.code || selectedCountry.currency || 'USD';
        const banks = selectedCountry.banks || [];

        console.log('Selected country:', selectedCountry.name, 'Currency:', currencyCode);

        setFormData(prev => ({
          ...prev,
          [name]: value,
          local_currency: currencyCode,
          main_bank: '' // Reset bank selection
        }));
        setAvailableBanks(banks);
      } else {
        setFormData(prev => ({ ...prev, [name]: value }));
      }
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!currentOrganization) {
      alert('No organization selected. Please ensure an organization is loaded.');
      console.error('currentOrganization is null/undefined:', currentOrganization);
      return;
    }

    if (!hasPermission(PERMISSIONS.CREATE_ENTITY)) {
      alert('You do not have permission to create entities');
      return;
    }

    try {
      // Map extended UI entity types to backend-supported choices
      const typeMapping = {
        public_company: 'corporation',
        public: 'corporation',
        holding_company: 'subsidiary',
        spv: 'other',
        trust: 'other',
        foundation: 'nonprofit',
        representative_office: 'branch',
        government_entity: 'other',
        joint_venture: 'partnership',
        sole_trader: 'sole_proprietor',
        llp: 'partnership',
      };

      const payload = {
        ...formData,
        entity_type: typeMapping[formData.entity_type] || formData.entity_type,
        organization_id: currentOrganization.id,
      };

      console.log('Creating entity with payload:', payload);
      await createEntity(payload);
      alert('Entity created successfully!');
      handleCloseModal();
      // Refresh entities list
      if (currentOrganization) {
        await fetchEntities(currentOrganization.id);
      }
    } catch (err) {
      console.error('Entity creation error:', err);
      alert('Failed to create entity: ' + err.message);
    }
  };

  const handleDeleteEntity = async (entity) => {
    if (!currentOrganization || !entity?.id) {
      return;
    }

    const confirmed = window.confirm(
      `Delete ${entity.name}? This will permanently remove the entity and its related records.`
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingEntityId(entity.id);
      await deleteEntity(entity.id, currentOrganization.id);
    } catch (err) {
      alert(`Failed to delete entity: ${err.message}`);
    } finally {
      setDeletingEntityId(null);
    }
  };

  const statusColors = {
    active:    { bg: 'rgba(23, 105, 224, 0.12)', color: '#1458bd', dot: '#1769e0' },
    dormant:   { bg: 'rgba(71, 85, 105, 0.10)', color: '#475569', dot: '#64748b' },
    wind_down: { bg: 'rgba(161, 98, 7, 0.12)', color: '#92400e', dot: '#b45309' },
  };

  const getStatusStyle = (status) => statusColors[status] || { bg: 'rgba(0, 0, 0, 0.06)', color: '#000000', dot: '#000000' };

  const openWorkspace = (entityId) => {
    const workspace = workspaceByEntityId[String(entityId)];
    if (!workspace?.id) {
      return;
    }
    navigate(`/app/workspace/${workspace.id}/overview`);
  };

  const openBusinessSuite = (entity) => {
    if (!entity?.id) {
      return;
    }

    if (entity.workspace_mode === 'workspace') {
      const workspace = workspaceByEntityId[String(entity.id)];
      if (workspace?.id) {
        navigate(`/app/workspace/${workspace.id}/overview`);
        return;
      }
    }

    if (entity.workspace_mode === 'equity') {
      navigate(`/app/equity/${entity.id}/registry`);
      return;
    }

    navigate(`/app/enterprise/entities/${entity.id}/dashboard`);
  };

  const kpis = [
    { label: 'Total Business Suites', value: entities.length, accent: '#000000' },
    { label: 'Active', value: entities.filter(e => e.status === 'active').length, accent: '#1769e0' },
    { label: 'Countries', value: new Set(entities.map(e => e.country)).size, accent: '#000000' },
    { label: 'Currencies', value: new Set(entities.map(e => e.local_currency)).size, accent: '#1769e0' },
  ];

  const creationActions = [
    {
      key: 'entity',
      title: 'Add Entity',
      description: 'Create a legal entity with accounting-focused setup and launch its dashboard.',
      path: '/app/entities/create?mode=accounting',
      accent: 'Accounting',
    },
    {
      key: 'workspace',
      title: 'Add Workspace',
      description: 'Create a combined operating workspace for accounting and equity workflows.',
      path: '/app/workspaces/new',
      accent: 'Operations',
    },
    {
      key: 'equity',
      title: 'Add Equity',
      description: 'Create an equity environment for cap table, vesting, grants, and ownership records.',
      path: '/app/equity/create',
      accent: 'Equity',
    },
  ];

  return (
    <div className="enterprise-action-page entities-page" style={{ maxWidth: 1300, margin: '0 auto' }}>

      <section className="action-page-hero">
        <div className="action-page-copy">
          <span className="action-page-kicker">Quick Action Destination</span>
          <h1 className="action-page-title">Business Suite</h1>
          <p className="action-page-subtitle">See every business suite dashboard, monitor operations, and drill into each organization structure from one place.</p>
          {hasPermission(PERMISSIONS.CREATE_ENTITY) && (
            <div className="action-page-actions">
              {creationActions.map((action) => (
                <button
                  key={action.key}
                  onClick={() => navigate(action.path)}
                  style={{ background: '#ffffff', color: '#000000', border: 'none', borderRadius: 999, padding: '10px 18px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
                >
                  {action.title}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="action-page-badge">{currentOrganization?.name || 'Organization'}</div>
      </section>

      <section className="action-page-stats">
        {kpis.slice(0, 3).map((kpi) => (
          <div key={kpi.label} className="action-page-stat">
            <span className="action-page-stat-label">{kpi.label}</span>
            <span className="action-page-stat-value">{kpi.value}</span>
            <span className="action-page-stat-caption">Business suite footprint across jurisdictions</span>
          </div>
        ))}
      </section>

      {error && (
        <div className="error-banner" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ flex: 1 }}>
            {error.includes('organizations')
              ? 'Could not load your organization. Please refresh the page or log in again.'
              : error}
          </span>
          <button className="btn-danger btn-sm" onClick={() => window.location.reload()}>Refresh</button>
        </div>
      )}

      {/* Entity Cards Grid */}
      {loading ? (
        <div className="loading">Loading business suites…</div>
      ) : entities.length === 0 ? (
        <div className="entity-empty-state">
          <div className="entity-empty-title">No business suites yet</div>
          <div className="entity-empty-text">Create your first business suite using one of the creation cards above.</div>
        </div>
      ) : (
        <div className="entity-cards-grid">
          {entities.map(entity => {
            const st = getStatusStyle(entity.status);
            return (
              <div
                key={entity.id}
                className="entity-card"
                onClick={() => openBusinessSuite(entity)}
              >
                <div className="entity-card-top">
                  <div className="entity-card-avatar">
                    {entity.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="badge" style={{ background: st.bg, color: st.color, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: st.dot, display: 'inline-block' }} />
                    {entity.status}
                  </span>
                </div>

                <div className="entity-card-name">{entity.name}</div>
                {entity.registration_number && (
                  <div className="entity-card-reg">Reg: {entity.registration_number}</div>
                )}

                <div className="entity-tag-row">
                  {[entity.country, entity.entity_type?.replace(/_/g, ' '), entity.local_currency].filter(Boolean).map((tag, i) => (
                    <span key={i} className="entity-tag">{tag}</span>
                  ))}
                </div>

                {entity.next_filing_date && (
                  <div className="entity-filing-date">
                    Next filing: <strong>{new Date(entity.next_filing_date).toLocaleDateString()}</strong>
                  </div>
                )}

                <div className="entity-card-actions" onClick={e => e.stopPropagation()}>
                  {workspaceByEntityId[String(entity.id)]?.id && (
                    <button
                      className="btn-secondary btn-sm"
                      style={{ flex: 1 }}
                      onClick={() => openWorkspace(entity.id)}
                    >
                      Workspace
                    </button>
                  )}
                  <button
                    className="btn-primary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => openBusinessSuite(entity)}
                  >Open Dashboard</button>
                  {hasPermission(PERMISSIONS.EDIT_ENTITY) && (
                    <button className="btn-secondary btn-sm" onClick={() => handleOpenModal(entity)}>Edit</button>
                  )}
                  {hasPermission(PERMISSIONS.DELETE_ENTITY) && (
                    <button
                      className="btn-danger btn-sm"
                      disabled={deletingEntityId === entity.id}
                      onClick={() => handleDeleteEntity(entity)}
                    >
                      {deletingEntityId === entity.id ? 'Deleting...' : 'Delete'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* All Entities Table */}
      {entities.length > 0 && (
        <div className="entity-table-section">
          <div className="entity-table-header">
            <h3 className="entity-table-title">All Business Suites</h3>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  {['Business Suite', 'Country', 'Type', 'Status', 'Currency', 'Filing Date', 'Actions'].map(h => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entities.map(entity => {
                  const st = getStatusStyle(entity.status);
                  return (
                    <tr
                      key={entity.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => openBusinessSuite(entity)}
                    >
                      <td>
                        <div style={{ fontWeight: 600 }}>{entity.name}</div>
                        {entity.registration_number && <div style={{ fontSize: 11, color: 'rgba(0, 0, 0, 0.48)' }}>{entity.registration_number}</div>}
                      </td>
                      <td className="table-row-muted">{entity.country}</td>
                      <td className="table-row-muted" style={{ textTransform: 'capitalize' }}>{entity.entity_type?.replace(/_/g, ' ')}</td>
                      <td>
                        <span className="badge" style={{ background: st.bg, color: st.color, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: st.dot, display: 'inline-block' }} />
                          {entity.status}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{entity.local_currency}</td>
                      <td className="table-row-muted">{entity.next_filing_date ? new Date(entity.next_filing_date).toLocaleDateString() : '—'}</td>
                      <td onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', gap: 6 }}>
                          {workspaceByEntityId[String(entity.id)]?.id && (
                            <button className="btn-secondary btn-sm" onClick={() => openWorkspace(entity.id)}>Workspace</button>
                          )}
                          <button className="btn-view btn-sm" onClick={() => openBusinessSuite(entity)}>View</button>
                          {hasPermission(PERMISSIONS.EDIT_ENTITY) && (
                            <button className="btn-secondary btn-sm" onClick={() => handleOpenModal(entity)}>Edit</button>
                          )}
                          {hasPermission(PERMISSIONS.DELETE_ENTITY) && (
                            <button
                              className="btn-danger btn-sm"
                              disabled={deletingEntityId === entity.id}
                              onClick={() => handleDeleteEntity(entity)}
                            >
                              {deletingEntityId === entity.id ? 'Deleting...' : 'Delete'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add / Edit Modal */}
      {showModal && (
        <div className="entity-modal-overlay" onClick={handleCloseModal}>
          <div className="entity-modal" onClick={e => e.stopPropagation()}>

            <div className="entity-modal-header">
              <h3 className="entity-modal-title">{editingEntity ? 'Edit Entity' : 'Add New Entity'}</h3>
              <button className="entity-modal-close" onClick={handleCloseModal}>×</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="entity-modal-body">
                <div className="entity-form-grid">

                  <div className="form-full">
                    <label className="entity-form-label">Entity Name *</label>
                    <input className="entity-form-input" type="text" name="name" value={formData.name} onChange={handleInputChange} required placeholder="e.g., Acme Corp USA" />
                  </div>

                  <div>
                    <label className="entity-form-label">Country *</label>
                    <select className="entity-form-input" name="country" value={formData.country} onChange={handleInputChange} required>
                      <option value="">Select a country</option>
                      {countryDropdownOptions.map(country => (
                        <option key={country.code} value={country.name}>{country.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="entity-form-label">Entity Type *</label>
                    <select className="entity-form-input" name="entity_type" value={formData.entity_type} onChange={handleInputChange}>
                      <option value="sole_proprietor">Sole Proprietor</option>
                      <option value="sole_trader">Sole Trader</option>
                      <option value="llc">LLC</option>
                      <option value="llp">LLP</option>
                      <option value="partnership">Partnership</option>
                      <option value="corporation">Corporation</option>
                      <option value="public_company">Public Company</option>
                      <option value="holding_company">Holding Company</option>
                      <option value="spv">SPV / Special Purpose Vehicle</option>
                      <option value="trust">Trust</option>
                      <option value="foundation">Foundation</option>
                      <option value="nonprofit">Nonprofit</option>
                      <option value="subsidiary">Subsidiary</option>
                      <option value="branch">Branch</option>
                      <option value="representative_office">Representative Office</option>
                      <option value="government_entity">Government / Public Sector</option>
                      <option value="joint_venture">Joint Venture</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="entity-form-label">Status</label>
                    <select className="entity-form-input" name="status" value={formData.status} onChange={handleInputChange}>
                      <option value="active">Active</option>
                      <option value="dormant">Dormant</option>
                      <option value="wind_down">In Wind-down</option>
                    </select>
                  </div>

                  <div>
                    <label className="entity-form-label">Registration Number</label>
                    <input className="entity-form-input" type="text" name="registration_number" value={formData.registration_number} onChange={handleInputChange} placeholder="e.g., EIN or company reg" />
                  </div>

                  <div>
                    <label className="entity-form-label">Local Currency</label>
                    <input className="entity-form-input" type="text" name="local_currency" value={formData.local_currency} readOnly />
                  </div>

                  <div>
                    <label className="entity-form-label">Main Bank</label>
                    <select className="entity-form-input" name="main_bank" value={formData.main_bank} onChange={handleInputChange}>
                      <option value="">Select a bank</option>
                      {availableBanks.map((bank, idx) => (
                        <option key={idx} value={bank}>{bank}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="entity-form-label">Fiscal Year End</label>
                    <input className="entity-form-input" type="date" name="fiscal_year_end" value={formData.fiscal_year_end} onChange={handleInputChange} />
                  </div>

                  <div>
                    <label className="entity-form-label">Next Filing Date</label>
                    <input className="entity-form-input" type="date" name="next_filing_date" value={formData.next_filing_date} onChange={handleInputChange} />
                  </div>

                </div>
              </div>

              <div className="entity-modal-footer">
                <button type="button" className="btn-secondary" onClick={handleCloseModal}>Cancel</button>
                <button type="submit" className="btn-primary">{editingEntity ? 'Update Entity' : 'Create Entity'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnterpriseEntities;
