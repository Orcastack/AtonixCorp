import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import '../../styles/EntityPages.css';
import './EnterpriseOverviewShared.css';
import './EnterpriseOverviewSections.css';
import './EnterpriseOrgOverview.css';

const REGION_MAP = {
  US: 'North America', CA: 'North America', MX: 'North America',
  GB: 'Europe', DE: 'Europe', FR: 'Europe', NL: 'Europe', IE: 'Europe',
  AE: 'Middle East', SA: 'Middle East', QA: 'Middle East',
  IN: 'Asia Pacific', SG: 'Asia Pacific', HK: 'Asia Pacific', AU: 'Asia Pacific',
  ZA: 'Africa', NG: 'Africa', KE: 'Africa', GH: 'Africa',
};

const formatCurrency = (value, options = {}) => `$${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: options.maximumFractionDigits ?? 0 })}`;

const formatCompactCurrency = (value) => '$' + (value >= 1000000
  ? (value / 1000000).toFixed(1) + 'M'
  : value >= 1000 ? (value / 1000).toFixed(0) + 'K' : value.toFixed(0));

const getRegion = (country) => {
  const code = country?.toUpperCase().slice(0, 2);
  return REGION_MAP[code] || 'Other';
};

const buildFinancialPositions = () => [
  { key: 'cash', label: 'Cash & Equivalents', value: '$0', metaLeft: '0 active accounts', metaRight: '0 currencies', icon: 'CA' },
  { key: 'investments', label: 'Investments', value: '$0', metaLeft: '0 holdings', metaRight: '0 asset classes', icon: 'IN' },
  { key: 'real-estate', label: 'Real Estate', value: '$0', metaLeft: '0 properties', metaRight: '0 countries', icon: 'RE' },
  { key: 'crypto', label: 'Cryptocurrency', value: '$0', metaLeft: '0 assets', metaRight: '24h: 0%', icon: 'BT' },
  { key: 'derivatives', label: 'Derivatives', value: '$0', metaLeft: '0 contracts', metaRight: '0 counterparties', icon: 'DV' },
  { key: 'private-equity', label: 'Private Equity', value: '$0', metaLeft: '0 investments', metaRight: '0 funds', icon: 'PE' },
];

const buildQuickActions = (handleNavigate) => [
  {
    key: 'entities',
    eyebrow: 'Structure',
    title: 'Manage Business Suite',
    description: 'Manage and monitor the full business suite across legal entities',
    path: '/app/enterprise/entities',
    accent: 'entities',
  },
  {
    key: 'team',
    eyebrow: 'Access',
    title: 'Manage Team',
    description: 'Control access and permissions',
    path: '/app/enterprise/team',
    accent: 'team',
  },
  {
    key: 'reports',
    eyebrow: 'Output',
    title: 'View Reports',
    description: 'Generate and export consolidated reports',
    path: '/app/enterprise/reports',
    accent: 'reports',
  },
  {
    key: 'compliance',
    eyebrow: 'Control',
    title: 'Tax Compliance',
    description: 'Track deadlines and obligations',
    path: '/app/enterprise/tax-compliance',
    accent: 'compliance',
  },
].map((action) => ({ ...action, onClick: () => handleNavigate(action.path) }));

const EnterpriseOrgOverview = () => {
  const navigate = useNavigate();
  const {
    currentOrganization,
    entities,
    orgOverview,
    fetchOrgOverview,
    fetchEntities,
    hasPermission,
    PERMISSIONS,
  } = useEnterprise();
  const [loading, setLoading] = useState(false);
  const [branchData, setBranchData] = useState([]);
  const [regionData, setRegionData] = useState({});
  const [activeTab, setActiveTab] = useState('overview');
  const [sortBy, setSortBy] = useState('revenue');

  const createdWorkspaces = (entities || []).filter((e) => e.workspace_mode === 'workspace');
  const createdEquity = (entities || []).filter((e) => e.workspace_mode === 'equity');
  const createdEntities = (entities || []).filter((e) => e.workspace_mode !== 'workspace' && e.workspace_mode !== 'equity');

  const buildBranchData = useCallback((entitiesList) => {
    const branches = entitiesList.map((entity) => ({
      id: entity.id,
      name: entity.name,
      country: entity.country,
      entity_type: entity.entity_type,
      status: entity.status,
      currency: entity.local_currency || 'USD',
      region: getRegion(entity.country),
      revenue: Math.floor(Math.random() * 2000000) + 100000,
      expenses: Math.floor(Math.random() * 1500000) + 80000,
      tax_exposure: Math.floor(Math.random() * 200000),
      staff_count: Math.floor(Math.random() * 50) + 1,
    }));

    branches.forEach((branch) => {
      branch.profit = branch.revenue - branch.expenses;
    });
    setBranchData(branches);

    const byRegion = {};
    branches.forEach((branch) => {
      if (!byRegion[branch.region]) {
        byRegion[branch.region] = { region: branch.region, entities: 0, revenue: 0, expenses: 0, profit: 0, countries: new Set() };
      }
      byRegion[branch.region].entities += 1;
      byRegion[branch.region].revenue += branch.revenue;
      byRegion[branch.region].expenses += branch.expenses;
      byRegion[branch.region].profit += branch.profit;
      byRegion[branch.region].countries.add(branch.country);
    });
    Object.values(byRegion).forEach((region) => {
      region.countries = region.countries.size;
    });
    setRegionData(byRegion);
  }, []);

  useEffect(() => {
    if (currentOrganization) {
      setLoading(true);
      fetchOrgOverview(currentOrganization.id);
      fetchEntities(currentOrganization.id);
    }
  }, [currentOrganization, fetchEntities, fetchOrgOverview]);

  useEffect(() => {
    if (!entities) {
      return;
    }

    if (entities.length > 0) {
      buildBranchData(entities);
    } else {
      setBranchData([]);
      setRegionData({});
    }
    setLoading(false);
  }, [buildBranchData, entities]);

  if (!hasPermission(PERMISSIONS.VIEW_ORG_OVERVIEW)) {
    return <div className="permission-denied">You don't have permission to view this dashboard.</div>;
  }

  if (!currentOrganization) {
    return <div className="loading">No organization yet. Create one to get started.</div>;
  }

  if (!orgOverview) {
    return <div className="loading">Loading organization overview...</div>;
  }

  const {
    total_assets = 0,
    total_liabilities = 0,
    net_position = 0,
    total_tax_exposure = 0,
    active_jurisdictions = 0,
    active_entities = 0,
    pending_tax_returns = 0,
    missing_data_entities = 0,
  } = orgOverview;

  const handleNavigate = (path) => {
    navigate(path);
  };

  const financialPositions = buildFinancialPositions();
  const quickActions = buildQuickActions(handleNavigate);
  const sortedBranches = [...branchData].sort((a, b) => {
    if (sortBy === 'revenue') return b.revenue - a.revenue;
    if (sortBy === 'profit') return b.profit - a.profit;
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    return 0;
  });
  const totalRevenue = branchData.reduce((sum, branch) => sum + branch.revenue, 0);
  const totalExpenses = branchData.reduce((sum, branch) => sum + branch.expenses, 0);
  const totalProfit = totalRevenue - totalExpenses;
  const regionCount = Object.keys(regionData).length;
  const profitMargin = totalRevenue ? (totalProfit / totalRevenue) * 100 : 0;
  const attentionCount = pending_tax_returns + missing_data_entities;

  return (
    <div className="enterprise-overview enterprise-dashboard org-overview-container ed-page org-dashboard-page">
      <div className="ed-header org-dashboard-header">
        <div className="org-dashboard-title-block">
          <h1 className="ed-entity-name">Organization Overview</h1>
          <p className="org-dashboard-organization">{currentOrganization.name}</p>
          <div className="ed-meta-row">
            <span className="ed-meta-item ed-meta-chip">{active_entities} active entities</span>
            <span className="ed-meta-sep">·</span>
            <span className="ed-meta-item ed-meta-chip">{active_jurisdictions} jurisdictions</span>
            <span className="ed-meta-sep">·</span>
            <span className="ed-meta-item ed-meta-chip">{regionCount} regions</span>
            <span className={`badge ed-meta-badge ${attentionCount > 0 ? 'dormant' : 'success'}`}>
              {attentionCount > 0 ? `${attentionCount} pending review` : 'Portfolio healthy'}
            </span>
          </div>
        </div>

        <div className="org-dashboard-actions">
          <button className="btn-secondary btn-sm" onClick={() => navigate('/app/enterprise/entities')}>Manage Business Suite</button>
          <button
            className="btn-primary btn-sm"
            onClick={() => {
              setLoading(true);
              fetchOrgOverview(currentOrganization.id);
              fetchEntities(currentOrganization.id);
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="ed-tabs org-dashboard-tabs">
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'branches', label: `Branches (${branchData.length})` },
          { key: 'regions', label: `Regions (${regionCount})` },
          { key: 'actions', label: 'Quick Actions' },
          { key: 'positions', label: 'Financial Positions' },
          { key: 'attention', label: `Attention (${attentionCount})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`ed-tab-btn${activeTab === tab.key ? ' active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="ed-content org-dashboard-content">
        {activeTab === 'overview' && (
          <div>
            <div className="summary-cards org-summary-cards" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
              <div className="summary-card profit">
                <div className="card-label">Net Position</div>
                <div className="card-value">{formatCurrency(net_position, { maximumFractionDigits: 2 })}</div>
                <div className="card-count">Assets {formatCurrency(total_assets)} vs liabilities {formatCurrency(total_liabilities)}</div>
              </div>
              <div className="summary-card expense">
                <div className="card-label">Tax Exposure</div>
                <div className="card-value">{formatCurrency(total_tax_exposure)}</div>
                <div className="card-count">{pending_tax_returns} returns pending this period</div>
              </div>
              <div className="summary-card income">
                <div className="card-label">Consolidated Revenue</div>
                <div className="card-value">{formatCompactCurrency(totalRevenue)}</div>
                <div className="card-count">{branchData.length} branches contributing</div>
              </div>
              <div className={`summary-card ${totalProfit >= 0 ? 'profit' : 'expense'}`}>
                <div className="card-label">Net Profit</div>
                <div className="card-value">{formatCompactCurrency(Math.abs(totalProfit))}</div>
                <div className="card-count">{profitMargin.toFixed(1)}% consolidated margin</div>
              </div>
            </div>

            <div className="ed-section">
              <h2 className="ed-section-title">Quick Actions</h2>
              <div className="ed-quick-access">
                {quickActions.map((action) => (
                  <button key={action.key} onClick={action.onClick} className={`ed-quick-card org-quick-card ${action.accent}`}>
                    <div className="org-quick-meta">{action.eyebrow}</div>
                    <div className="ed-quick-label">{action.title}</div>
                    <div className="card-count">{action.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {loading && (
              <div className="ed-loading">
                <div className="spinner" />Loading enterprise data...
              </div>
            )}

            {!loading && branchData.length === 0 && (
              <div className="ed-onboarding org-dashboard-onboarding">
                <div className="ed-onboarding-header">
                  <div className="ed-onboarding-kpi-row">
                    <div className="ed-ob-kpi">
                      <div className="ed-ob-kpi-value">0</div>
                      <div className="ed-ob-kpi-label">Active Entities</div>
                    </div>
                    <div className="ed-ob-kpi">
                      <div className="ed-ob-kpi-value">$0</div>
                      <div className="ed-ob-kpi-label">Consolidated Revenue</div>
                    </div>
                    <div className="ed-ob-kpi">
                      <div className="ed-ob-kpi-value">$0</div>
                      <div className="ed-ob-kpi-label">Total Tax Exposure</div>
                    </div>
                    <div className="ed-ob-kpi">
                      <div className="ed-ob-kpi-value">0</div>
                      <div className="ed-ob-kpi-label">Jurisdictions</div>
                    </div>
                  </div>
                </div>

                <div className="ed-onboarding-body">
                  <div className="ed-ob-left">
                    <div className="ed-ob-step-label">Getting Started</div>
                    <h2 className="ed-ob-title">Set up your Enterprise Structure</h2>
                    <p className="ed-ob-desc">
                      Add legal entities to unlock multi-branch financial consolidation, regional P&amp;L,
                      tax exposure tracking, and cross-entity reporting.
                    </p>
                    <div className="ed-ob-steps">
                      <div className="ed-ob-step">
                        <div className="ed-ob-step-num">1</div>
                        <div>
                          <div className="ed-ob-step-title">Create an entity</div>
                          <div className="ed-ob-step-sub">Add a subsidiary, branch, or holding company</div>
                        </div>
                      </div>
                      <div className="ed-ob-step">
                        <div className="ed-ob-step-num">2</div>
                        <div>
                          <div className="ed-ob-step-title">Assign jurisdiction &amp; currency</div>
                          <div className="ed-ob-step-sub">Set the operating country and local currency</div>
                        </div>
                      </div>
                      <div className="ed-ob-step">
                        <div className="ed-ob-step-num">3</div>
                        <div>
                          <div className="ed-ob-step-title">Connect accounting</div>
                          <div className="ed-ob-step-sub">Import or record transactions for consolidated reporting</div>
                        </div>
                      </div>
                      <div className="ed-ob-step">
                        <div className="ed-ob-step-num">4</div>
                        <div>
                          <div className="ed-ob-step-title">View consolidated dashboard</div>
                          <div className="ed-ob-step-sub">Revenue, profit, and tax across all branches appear here</div>
                        </div>
                      </div>
                    </div>
                    <div className="ed-ob-actions">
                      <button className="btn-primary btn-sm" onClick={() => navigate('/app/enterprise/entities')}>
                        Go to Business Suite
                      </button>
                    </div>
                  </div>

                  <div className="ed-ob-right">
                    <div className="ed-ob-preview-label">Preview - With entities, you will see:</div>
                    <div className="ed-ob-preview-cards">
                      <div className="ed-ob-preview-card">
                        <div className="ed-ob-preview-row">
                          <span className="ed-ob-preview-dot cyan" />
                          <span>Revenue by Branch</span>
                        </div>
                        <div className="ed-ob-preview-bar-track">
                          <div className="ed-ob-preview-bar-fill" style={{ width: '80%', background: 'var(--color-cyan)' }} />
                        </div>
                        <div className="ed-ob-preview-bar-track" style={{ marginTop: 6 }}>
                          <div className="ed-ob-preview-bar-fill" style={{ width: '55%', background: 'var(--color-cyan-dark)' }} />
                        </div>
                        <div className="ed-ob-preview-bar-track" style={{ marginTop: 6 }}>
                          <div className="ed-ob-preview-bar-fill" style={{ width: '35%', background: 'var(--color-silver-dark)' }} />
                        </div>
                      </div>
                      <div className="ed-ob-preview-card">
                        <div className="ed-ob-preview-row">
                          <span className="ed-ob-preview-dot green" />
                          <span>Regional P&amp;L Breakdown</span>
                        </div>
                        <div className="ed-ob-preview-region-list">
                          <div className="ed-ob-preview-region">
                            <span>North America</span><span className="pos">+$1.2M</span>
                          </div>
                          <div className="ed-ob-preview-region">
                            <span>Europe</span><span className="pos">+$840K</span>
                          </div>
                          <div className="ed-ob-preview-region">
                            <span>Middle East</span><span className="pos">+$480K</span>
                          </div>
                        </div>
                      </div>
                      <div className="ed-ob-preview-card">
                        <div className="ed-ob-preview-row">
                          <span className="ed-ob-preview-dot orange" />
                          <span>Tax Exposure by Jurisdiction</span>
                        </div>
                        <div className="ed-ob-preview-region-list">
                          <div className="ed-ob-preview-region">
                            <span>US Federal + State</span><span>$142K</span>
                          </div>
                          <div className="ed-ob-preview-region">
                            <span>UK Corporation Tax</span><span>$88K</span>
                          </div>
                          <div className="ed-ob-preview-region">
                            <span>UAE Corporate Tax</span><span>$34K</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!loading && branchData.length > 0 && (
              <div className="chart-grid org-dashboard-panels">
                <div className="chart-card org-dashboard-panel">
                  <div className="org-panel-head">
                    <h3>Top Branches</h3>
                    <span>Ranked by revenue contribution</span>
                  </div>
                  <div className="org-performance-list">
                    {sortedBranches.slice(0, 5).map((branch) => {
                      const pct = totalRevenue ? (branch.revenue / totalRevenue) * 100 : 0;
                      return (
                        <button
                          key={branch.id}
                          className="perf-bar-row org-performance-row"
                          onClick={() => navigate(`/app/enterprise/entities/${branch.id}/dashboard`)}
                        >
                          <div className="pbr-label">
                            <span className="pbr-name">{branch.name}</span>
                            <span className="pbr-country">{branch.country}</span>
                          </div>
                          <div className="pbr-track">
                            <div
                              className="pbr-fill"
                              style={{ width: `${pct}%`, background: branch.profit >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}
                            />
                          </div>
                          <div className="pbr-values">
                            <span className="pbr-rev">{formatCompactCurrency(branch.revenue)}</span>
                            <span className={`pbr-profit ${branch.profit >= 0 ? 'pos' : 'neg'}`}>
                              {formatCompactCurrency(Math.abs(branch.profit))}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="chart-card org-dashboard-panel">
                  <div className="org-panel-head">
                    <h3>Regional Snapshot</h3>
                    <span>Operating concentration by region</span>
                  </div>
                  <div className="org-region-snapshot-list">
                    {Object.values(regionData)
                      .sort((a, b) => b.revenue - a.revenue)
                      .slice(0, 5)
                      .map((region) => (
                        <div className="org-region-snapshot-item" key={region.region}>
                          <div>
                            <strong>{region.region}</strong>
                            <div className="table-row-muted">{region.entities} entities across {region.countries} countries</div>
                          </div>
                          <div className="org-region-snapshot-metrics">
                            <span>{formatCompactCurrency(region.revenue)}</span>
                            <span className={region.profit >= 0 ? 'pos' : 'neg'}>{formatCompactCurrency(Math.abs(region.profit))}</span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── Created Workspaces ───────────────────────────── */}
        {activeTab === 'overview' && createdWorkspaces.length > 0 && (
          <div className="overview-resource-group">
            <div className="org-group-header">
              <h3 className="org-group-title">Workspaces</h3>
              <button className="org-group-add" onClick={() => navigate('/app/workspaces/new')}>+ New Workspace</button>
            </div>
            <div className="org-resource-grid">
              {createdWorkspaces.map((ws) => (
                <div className="org-resource-card" key={ws.id}>
                  <div className="orc-top">
                    <span className="orc-type">{ws.workspace_type || ws.entity_type || 'Workspace'}</span>
                    <span className={`orc-status orc-status--${ws.status || 'active'}`}>{ws.status || 'active'}</span>
                  </div>
                  <div className="orc-name">{ws.name}</div>
                  <div className="orc-meta">{ws.country || ''}{ws.industry ? ` · ${ws.industry}` : ''}</div>
                  <div className="orc-meta">{ws.created_at ? new Date(ws.created_at).toLocaleDateString() : ''}</div>
                  <div className="orc-actions">
                    <button className="orc-btn" onClick={() => navigate(`/app/workspace/${ws.id}/overview`)}>Open</button>
                    <button className="orc-btn" onClick={() => navigate(`/app/workspace/${ws.id}/settings`)}>Settings</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── Created Entities ─────────────────────────────── */}
        {activeTab === 'overview' && createdEntities.length > 0 && (
          <div className="overview-resource-group">
            <div className="org-group-header">
              <h3 className="org-group-title">Legal Entities</h3>
              <button className="org-group-add" onClick={() => navigate('/app/entities/create?mode=accounting')}>+ New Entity</button>
            </div>
            <div className="org-resource-grid">
              {createdEntities.map((ent) => (
                <div className="org-resource-card" key={ent.id}>
                  <div className="orc-top">
                    <span className="orc-type">{ent.entity_type || 'Entity'}</span>
                    <span className={`orc-status orc-status--${ent.status || 'active'}`}>{ent.status || 'active'}</span>
                  </div>
                  <div className="orc-name">{ent.name}</div>
                  <div className="orc-meta">{ent.country || ''}{ent.local_currency ? ` · ${ent.local_currency}` : ''}</div>
                  <div className="orc-meta">{ent.created_at ? new Date(ent.created_at).toLocaleDateString() : ''}</div>
                  <div className="orc-actions">
                    <button className="orc-btn" onClick={() => navigate(`/app/enterprise/entities/${ent.id}/dashboard`)}>Open</button>
                    <button className="orc-btn" onClick={() => navigate(`/app/enterprise/entities/${ent.id}/settings`)}>Settings</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── Created Equity Structures ────────────────────── */}
        {activeTab === 'overview' && createdEquity.length > 0 && (
          <div className="overview-resource-group">
            <div className="org-group-header">
              <h3 className="org-group-title">Equity Structures</h3>
              <button className="org-group-add" onClick={() => navigate('/app/equity/create')}>+ New Equity Structure</button>
            </div>
            <div className="org-resource-grid">
              {createdEquity.map((eq) => (
                <div className="org-resource-card" key={eq.id}>
                  <div className="orc-top">
                    <span className="orc-type">{eq.entity_type || 'Equity'}</span>
                    <span className={`orc-status orc-status--${eq.status || 'active'}`}>{eq.status || 'active'}</span>
                  </div>
                  <div className="orc-name">{eq.name}</div>
                  <div className="orc-meta">{eq.country || ''}{eq.local_currency ? ` · ${eq.local_currency}` : ''}</div>
                  <div className="orc-meta">{eq.created_at ? new Date(eq.created_at).toLocaleDateString() : ''}</div>
                  <div className="orc-actions">
                    <button className="orc-btn" onClick={() => navigate(`/app/equity/${eq.id}/registry`)}>Open</button>
                    <button className="orc-btn" onClick={() => navigate(`/app/enterprise/entities/${eq.id}/dashboard`)}>Settings</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'branches' && branchData.length > 0 && (
          <section className="overview-band">
          <div className="section-heading-row">
            <h2 className="section-title">Branch Overview</h2>
            <span className="section-caption">{branchData.length} entities ranked by {sortBy}</span>
          </div>

          <div className="overview-toolbar org-tab-toolbar">
            <div className="org-tab-summary">Compare branch contribution and jump straight into each entity dashboard.</div>
            <div className="overview-select">
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="revenue">Sort by Revenue</option>
                <option value="profit">Sort by Profit</option>
                <option value="name">Sort by Name</option>
              </select>
            </div>
          </div>

          <div className="ent-card">
            <div className="ent-card-header">
              <h3 className="ent-card-title">Revenue by Branch</h3>
            </div>
            {sortedBranches.map((branch) => {
              const pct = totalRevenue ? (branch.revenue / totalRevenue) * 100 : 0;
              return (
                <div
                  className="perf-bar-row"
                  key={branch.id}
                  onClick={() => navigate(`/app/enterprise/entities/${branch.id}/dashboard`)}
                >
                  <div className="pbr-label">
                    <span className="pbr-name">{branch.name}</span>
                    <span className="pbr-country">{branch.country}</span>
                  </div>
                  <div className="pbr-track">
                    <div
                      className="pbr-fill"
                      style={{ width: `${pct}%`, background: branch.profit >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}
                    />
                  </div>
                  <div className="pbr-values">
                    <span className="pbr-rev">{formatCompactCurrency(branch.revenue)}</span>
                    <span className={`pbr-profit ${branch.profit >= 0 ? 'pos' : 'neg'}`}>
                      {formatCompactCurrency(Math.abs(branch.profit))}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid-12 section-gap-sm">
            {sortedBranches.map((branch) => (
              <div className="col-4" key={branch.id}>
                <div
                  className="ent-card ent-card--clickable"
                  onClick={() => navigate(`/app/enterprise/entities/${branch.id}/dashboard`)}
                >
                  <div className="ebc-header">
                    <div className="ebc-flag">{branch.country}</div>
                    <span className={`status-pill ${branch.status}`}>{branch.status}</span>
                  </div>
                  <div className="ebc-name">{branch.name}</div>
                  <div className="ebc-type">{branch.entity_type?.replace('_', '')}</div>
                  <div className="ebc-region">{branch.region}</div>
                  <div className="ebc-metrics">
                    <div className="ebc-metric">
                      <span>Revenue</span>
                      <strong>{formatCompactCurrency(branch.revenue)}</strong>
                    </div>
                    <div className="ebc-metric">
                      <span>Expenses</span>
                      <strong>{formatCompactCurrency(branch.expenses)}</strong>
                    </div>
                    <div className="ebc-metric">
                      <span>Profit</span>
                      <strong className={branch.profit >= 0 ? 'pos' : 'neg'}>
                        {formatCompactCurrency(Math.abs(branch.profit))}
                      </strong>
                    </div>
                    <div className="ebc-metric">
                      <span>Tax Exp</span>
                      <strong>{formatCompactCurrency(branch.tax_exposure)}</strong>
                    </div>
                  </div>
                  <div className="ebc-margin-bar">
                    <div
                      style={{
                        width: `${branch.revenue ? Math.max(0, (branch.profit / branch.revenue) * 100) : 0}%`,
                        background: branch.profit >= 0 ? 'var(--color-success)' : 'var(--color-error)',
                      }}
                    />
                  </div>
                  <div className="ebc-margin-label">
                    {branch.revenue ? ((branch.profit / branch.revenue) * 100).toFixed(1) : 0}% margin
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
        )}

        {activeTab === 'branches' && !loading && branchData.length === 0 && (
          <div className="empty-state">
            <p className="empty-state-text">No entities available yet. Add your first entity to unlock branch comparisons and direct dashboard access.</p>
          </div>
        )}

        {activeTab === 'regions' && Object.keys(regionData).length > 0 && (
          <section className="overview-band">
          <div className="section-heading-row">
            <h2 className="section-title">Regional Operations</h2>
            <span className="section-caption">{Object.keys(regionData).length} regions by contribution to total revenue</span>
          </div>
          <div className="grid-12">
            {Object.values(regionData)
              .sort((a, b) => b.revenue - a.revenue)
              .map((region) => (
                <div className="col-4" key={region.region}>
                  <div className="ent-card ent-card--clickable">
                    <div className="erc-header">
                      <div className="erc-icon">RG</div>
                      <div>
                        <div className="erc-name">{region.region}</div>
                        <div className="erc-meta">
                          {region.entities} entities · {region.countries} countries
                        </div>
                      </div>
                    </div>
                    <div className="erc-metrics">
                      <div className="erc-metric">
                        <span>Revenue</span>
                        <strong>{formatCompactCurrency(region.revenue)}</strong>
                      </div>
                      <div className="erc-metric">
                        <span>Expenses</span>
                        <strong>{formatCompactCurrency(region.expenses)}</strong>
                      </div>
                      <div className="erc-metric">
                        <span>Net Profit</span>
                        <strong className={region.profit >= 0 ? 'pos' : 'neg'}>
                          {formatCompactCurrency(Math.abs(region.profit))}
                        </strong>
                      </div>
                    </div>
                    <div className="erc-contribution">
                      <span>Revenue contribution</span>
                      <div className="erc-bar-track">
                        <div
                          className="erc-bar-fill"
                          style={{ width: `${totalRevenue ? (region.revenue / totalRevenue) * 100 : 0}%` }}
                        />
                      </div>
                      <span>{totalRevenue ? ((region.revenue / totalRevenue) * 100).toFixed(0) : 0}%</span>
                    </div>
                    <div className="erc-entities">
                      {branchData
                        .filter((branch) => branch.region === region.region)
                        .map((branch) => (
                          <div
                            className="erc-entity-chip"
                            key={branch.id}
                            onClick={() => navigate(`/app/enterprise/entities/${branch.id}/dashboard`)}
                          >
                            {branch.name}
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </section>
        )}

        {activeTab === 'regions' && !loading && Object.keys(regionData).length === 0 && (
          <div className="empty-state">
            <p className="empty-state-text">Regional insights will appear here once entity locations and financial activity are available.</p>
          </div>
        )}

        {activeTab === 'actions' && (
          <section className="overview-band">
            <div className="section-heading-row">
              <h2 className="section-title">Quick Actions</h2>
              <span className="section-caption">Jump directly into operational workflows</span>
            </div>

            <div className="actions-grid">
              {quickActions.map((action) => (
                <button key={action.key} className={`action-button ${action.accent}`} onClick={action.onClick}>
                  <div className="action-icon">{action.title.slice(0, 2).toUpperCase()}</div>
                  <div className="action-content">
                    <span className="action-eyebrow">{action.eyebrow}</span>
                    <h4>{action.title}</h4>
                    <p>{action.description}</p>
                  </div>
                  <span className="action-arrow">Open</span>
                </button>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'attention' && (
          <section className="overview-band">
          <div className="section-heading-row">
            <h2 className="section-title">Action Required</h2>
            <span className="section-caption">Exceptions that need attention before close and filing</span>
          </div>
          <div className="ent-card">
            <div className="ent-card-header">
              <h3 className="ent-card-title ent-card-title--with-icon">Action Required</h3>
            </div>
            {attentionCount > 0 ? (
              <div className="ed-alert-list">
                {pending_tax_returns > 0 && (
                <div className="ed-alert-item warning">
                  <span>{pending_tax_returns} tax return(s) pending. Review compliance status.</span>
                  <button
                    className="btn-alert-action"
                    onClick={() => navigate('/app/enterprise/tax-compliance')}
                  >View
                  </button>
                </div>
                )}
                {missing_data_entities > 0 && (
                <div className="ed-alert-item info">
                  <span>{missing_data_entities} entity(ies) have incomplete data.</span>
                  <button
                    className="btn-alert-action"
                    onClick={() => navigate('/app/enterprise/entities')}
                  >Fix
                  </button>
                </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <p className="empty-state-text">No critical action items right now. Compliance and entity data are in a healthy state.</p>
              </div>
            )}
          </div>
        </section>
        )}

        {activeTab === 'positions' && (
          <section className="active-positions">
        <div className="section-heading-row">
          <h3 className="section-title">Active Financial Positions</h3>
          <span className="section-caption">Current exposure by balance sheet bucket</span>
        </div>

        <div className="positions-grid">
          {financialPositions.map((position) => (
            <div key={position.key} className={`position-card ${position.key}`}>
              <div className="position-header">
                <div className="position-icon">{position.icon}</div>
                <h4>{position.label}</h4>
              </div>
              <div className="position-value">{position.value}</div>
              <div className="position-details">
                <span>{position.metaLeft}</span>
                <span>{position.metaRight}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
        )}
      </div>
    </div>
  );
};

export default EnterpriseOrgOverview;
