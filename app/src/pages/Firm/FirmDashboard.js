import React, { useEffect, useState, useCallback } from 'react';
import { useEnterprise } from '../../context/EnterpriseContext';
import { getApiBaseUrl } from '../../utils/apiBaseUrl';

const API_BASE = getApiBaseUrl();

const EMPTY_DASHBOARD = {
  clients: { total: 0, active: 0, inactive: 0, prospects: 0, recent: [] },
  workload: { total: 0, pending: 0, in_progress: 0, completed: 0, overdue: 0, by_entity: [] },
  staff: { total: 0, performance: [] },
  billing: { total_invoiced: 0, total_paid: 0, overdue_count: 0 },
};

const FirmDashboard = () => {
  const { currentOrganization } = useEnterprise();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [clientSearch, setClientSearch] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const fetchDashboard = useCallback(async () => {
    if (!currentOrganization) return;
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(
        `${API_BASE}/organizations/${currentOrganization.id}/firm_dashboard/`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Failed to fetch firm dashboard');
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message);
      setData(EMPTY_DASHBOARD);
    } finally {
      setLoading(false);
    }
  }, [currentOrganization]);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  const filteredClients = data?.clients?.recent?.filter(c =>
    c.name.toLowerCase().includes(clientSearch.toLowerCase()) ||
    c.industry?.toLowerCase().includes(clientSearch.toLowerCase())
  ) || [];

  const getStatusBadge = (status) => {
    const map = {
      active: 'badge-success', inactive: 'badge-secondary',
      prospect: 'badge-warning', pending: 'badge-warning',
      overdue: 'badge-danger'
    };
    return `badge ${map[status] || 'badge-secondary'}`;
  };

  const completionRate = (staff) => {
    const total = staff.tasks_assigned + staff.tasks_completed;
    if (!total) return 0;
    return Math.round((staff.tasks_completed / total) * 100);
  };

  if (!currentOrganization) {
    return (
      <div className="firm-dashboard">
        <div className="empty-state">

          <h2>No Organization Selected</h2>
          <p>Please create or select an organization to view the Firm Dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="firm-dashboard">
      {/* Header */}
      <div className="fd-header">
        <div className="fd-header-left">
          <h1>Firm Dashboard</h1>
          <p>{currentOrganization.name} &mdash; Command Center</p>
        </div>
        <button className="btn-refresh" onClick={fetchDashboard} disabled={loading}>
          Refresh
        </button>
      </div>

      {error && <div className="alert-warning">Data unavailable: {error}</div>}

      {/* KPI Strip */}
      {data && (
        <div className="fd-kpi-strip">
          <div className="kpi-card kpi-blue">
            <div className="kpi-icon"></div>
            <div className="kpi-body">
              <div className="kpi-value">{data.clients.total}</div>
              <div className="kpi-label">Total Clients</div>
              <div className="kpi-sub">{data.clients.active} active · {data.clients.prospects} prospects</div>
            </div>
          </div>
          <div className="kpi-card kpi-purple">
            <div className="kpi-icon"></div>
            <div className="kpi-body">
              <div className="kpi-value">{data.workload.total}</div>
              <div className="kpi-label">Total Tasks</div>
              <div className="kpi-sub">{data.workload.in_progress} in progress · {data.workload.overdue} overdue</div>
            </div>
          </div>
          <div className="kpi-card kpi-green">
            <div className="kpi-icon"></div>
            <div className="kpi-body">
              <div className="kpi-value">{data.staff.total}</div>
              <div className="kpi-label">Staff Members</div>
              <div className="kpi-sub">Across all entities</div>
            </div>
          </div>
          <div className="kpi-card kpi-orange">
            <div className="kpi-icon"></div>
            <div className="kpi-body">
              <div className="kpi-value">${(data.billing.total_invoiced / 1000).toFixed(0)}K</div>
              <div className="kpi-label">Total Invoiced</div>
              <div className="kpi-sub">${(data.billing.total_paid / 1000).toFixed(0)}K collected · {data.billing.overdue_count} overdue</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="fd-tabs">
        {[
          { key: 'overview', label: 'Overview', },
          { key: 'clients', label: 'All Clients', },
          { key: 'workload', label: 'Workload', },
          { key: 'staff', label: 'Staff Performance', },
        ].map(tab => (
          <button
            key={tab.key}
            className={`fd-tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {loading && <div className="fd-loading"><div className="spinner" />Loading dashboard...</div>}

      {!loading && data && (
        <>
          {/*  OVERVIEW TAB  */}
          {activeTab === 'overview' && (
            <div className="fd-grid">
              {/* Workload summary donut-like bar */}
              <div className="fd-card fd-workload-summary">
                <h3>Workload Overview</h3>
                <div className="workload-bars">
                  {[
                    { label: 'Pending', value: data.workload.pending, color: 'var(--color-warning)', total: data.workload.total },
                    { label: 'In Progress', value: data.workload.in_progress, color: 'var(--color-cyan)', total: data.workload.total },
                    { label: 'Completed', value: data.workload.completed, color: 'var(--color-success)', total: data.workload.total },
                    { label: 'Overdue', value: data.workload.overdue, color: 'var(--color-error)', total: data.workload.total },
                  ].map(item => (
                    <div className="workload-bar-row" key={item.label}>
                      <span className="wb-label">{item.label}</span>
                      <div className="wb-track">
                        <div className="wb-fill" style={{
                          width: `${item.total ? (item.value / item.total) * 100 : 0}%`,
                          background: item.color
                        }} />
                      </div>
                      <span className="wb-count">{item.value}</span>
                    </div>
                  ))}
                </div>
                <div className="workload-by-entity">
                  <h4>Tasks by Entity</h4>
                  {data.workload.by_entity.map((row, i) => (
                    <div className="entity-task-row" key={i}>
                      <span>{row.entity__name || row['entity__name']}</span>
                      <span className="entity-task-count">{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Clients */}
              <div className="fd-card fd-recent-clients">
                <h3>Recent Clients</h3>
                <div className="client-list">
                  {data.clients.recent.slice(0, 5).map(client => (
                    <div className="client-row" key={client.id}>
                      <div className="client-avatar">{client.name[0]}</div>
                      <div className="client-info">
                        <div className="client-name">{client.name}</div>
                        <div className="client-meta">{client.industry} · {client.email}</div>
                      </div>
                      <span className={getStatusBadge(client.status)}>{client.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Staff Top Performers */}
              <div className="fd-card fd-staff-top">
                <h3>Top Performers</h3>
                <div className="staff-list">
                  {[...data.staff.performance]
                    .sort((a, b) => b.tasks_completed - a.tasks_completed)
                    .slice(0, 5)
                    .map(staff => (
                      <div className="staff-row" key={staff.id}>
                        <div className="staff-avatar">{staff.name[0]}</div>
                        <div className="staff-info">
                          <div className="staff-name">{staff.name}</div>
                          <div className="staff-meta">{staff.role} &mdash; {staff.entity}</div>
                        </div>
                        <div className="staff-score">
                          <div className="score-num">{completionRate(staff)}%</div>
                          <div className="score-label">done</div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Billing */}
              <div className="fd-card fd-billing">
                <h3>Billing Summary</h3>
                <div className="billing-metric">
                  <span>Total Invoiced</span>
                  <strong>${data.billing.total_invoiced.toLocaleString()}</strong>
                </div>
                <div className="billing-progress-track">
                  <div className="billing-progress-fill" style={{
                    width: `${data.billing.total_invoiced ? (data.billing.total_paid / data.billing.total_invoiced) * 100 : 0}%`
                  }} />
                </div>
                <div className="billing-metric">
                  <span>Collected</span>
                  <strong className="text-success">${data.billing.total_paid.toLocaleString()}</strong>
                </div>
                <div className="billing-metric">
                  <span>Outstanding</span>
                  <strong className="text-warning">
                    ${(data.billing.total_invoiced - data.billing.total_paid).toLocaleString()}
                  </strong>
                </div>
                {data.billing.overdue_count > 0 && (
                  <div className="billing-alert">
                     {data.billing.overdue_count} overdue invoice(s)
                  </div>
                )}
              </div>
            </div>
          )}

          {/*  CLIENTS TAB  */}
          {activeTab === 'clients' && (
            <div className="fd-section">
              <div className="fd-section-toolbar">
                <div className="search-box">

                  <input
                    type="text"
                    placeholder="Search clients..."
                    value={clientSearch}
                    onChange={e => setClientSearch(e.target.value)}
                  />
                </div>
                <div className="client-status-pills">
                  {[
                    { label: 'All', count: data.clients.total },
                    { label: 'Active', count: data.clients.active },
                    { label: 'Prospects', count: data.clients.prospects },
                    { label: 'Inactive', count: data.clients.inactive },
                  ].map(p => (
                    <span className="status-pill" key={p.label}>
                      {p.label} <strong>{p.count}</strong>
                    </span>
                  ))}
                </div>
              </div>
              <div className="clients-table-wrap">
                <table className="fd-table">
                  <thead>
                    <tr>
                      <th>Client</th>
                      <th>Industry</th>
                      <th>Email</th>
                      <th>Status</th>
                      <th>Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredClients.map(client => (
                      <tr key={client.id}>
                        <td>
                          <div className="td-client">
                            <div className="client-avatar sm">{client.name[0]}</div>
                            <span>{client.name}</span>
                          </div>
                        </td>
                        <td>{client.industry || '—'}</td>
                        <td>{client.email}</td>
                        <td><span className={getStatusBadge(client.status)}>{client.status}</span></td>
                        <td>{client.created_at ? new Date(client.created_at).toLocaleDateString() : '—'}</td>
                      </tr>
                    ))}
                    {filteredClients.length === 0 && (
                      <tr><td colSpan={5} className="no-results">No clients match your search.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/*  WORKLOAD TAB  */}
          {activeTab === 'workload' && (
            <div className="fd-section">
              <div className="workload-grid">
                {[
                  { label: 'Pending', value: data.workload.pending, color: 'var(--color-warning)', },
                  { label: 'In Progress', value: data.workload.in_progress, color: 'var(--color-cyan)', },
                  { label: 'Completed', value: data.workload.completed, color: 'var(--color-success)', },
                  { label: 'Overdue', value: data.workload.overdue, color: 'var(--color-error)', },
                ].map(item => (
                  <div className="wl-stat-card" key={item.label} style={{ borderTop: `4px solid ${item.color}` }}>
                    <div className="wl-icon" style={{ color: item.color }}>{item.icon}</div>
                    <div className="wl-value">{item.value}</div>
                    <div className="wl-label">{item.label}</div>
                  </div>
                ))}
              </div>
              <div className="fd-card">
                <h3>Task Distribution by Entity</h3>
                {data.workload.by_entity.map((row, i) => {
                  const pct = data.workload.total ? (row.count / data.workload.total) * 100 : 0;
                  return (
                    <div className="entity-dist-row" key={i}>
                      <span className="ent-name">{row.entity__name || row['entity__name']}</span>
                      <div className="ent-bar-track">
                        <div className="ent-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="ent-count">{row.count} tasks ({pct.toFixed(0)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/*  STAFF PERFORMANCE TAB  */}
          {activeTab === 'staff' && (
            <div className="fd-section">
              <div className="staff-perf-grid">
                {data.staff.performance.map(staff => {
                  const rate = completionRate(staff);
                  return (
                    <div className="staff-perf-card" key={staff.id}>
                      <div className="spc-header">
                        <div className="spc-avatar">{staff.name[0]}</div>
                        <div>
                          <div className="spc-name">{staff.name}</div>
                          <div className="spc-role">{staff.role}</div>
                          <div className="spc-entity">{staff.entity}</div>
                        </div>
                        {staff.is_active
                          ? <span className="badge badge-success ml-auto">Active</span>
                          : <span className="badge badge-secondary ml-auto">Inactive</span>
                        }
                      </div>
                      <div className="spc-metrics">
                        <div className="spc-metric">
                          <span>Assigned</span>
                          <strong>{staff.tasks_assigned}</strong>
                        </div>
                        <div className="spc-metric">
                          <span>Completed</span>
                          <strong className="text-success">{staff.tasks_completed}</strong>
                        </div>
                        <div className="spc-metric">
                          <span>Completion</span>
                          <strong>{rate}%</strong>
                        </div>
                      </div>
                      <div className="spc-progress-track">
                        <div className="spc-progress-fill" style={{ width: `${rate}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default FirmDashboard;
