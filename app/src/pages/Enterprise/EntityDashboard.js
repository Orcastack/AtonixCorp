import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import '../../styles/EntityPages.css';

const EntityDashboard = () => {
  const { entityId } = useParams();
  const navigate = useNavigate();
  const enterpriseContext = useEnterprise();
  const didRequestEntitiesRef = useRef(false);

  // Safely destructure with fallbacks
  const {
    entities = [],
    currentOrganization,
    fetchEntities,
    fetchEntityExpenses,
    fetchEntityIncome,
    fetchEntityBudgets,
    fetchEntityDepartments,
    fetchEntityRoles,
    fetchEntityStaff,
    fetchEntityBankAccounts,
    fetchEntityWallets,
    fetchEntityComplianceDocuments,
    activeWorkspace,
    hasPermission,
    PERMISSIONS
  } = enterpriseContext || {};

  const resolvedEntityId = useMemo(() => {
    const directEntityId = Number(entityId);
    if (Number.isInteger(directEntityId) && String(directEntityId) === String(entityId).trim()) {
      return directEntityId;
    }

    const workspaceCandidates = [activeWorkspace];
    try {
      const savedWorkspace = localStorage.getItem('ledgora_active_workspace');
      if (savedWorkspace) {
        workspaceCandidates.push(JSON.parse(savedWorkspace));
      }
    } catch {
      // Ignore malformed saved workspace state.
    }

    const matchingWorkspace = workspaceCandidates.find((workspace) => workspace && String(workspace.id) === String(entityId));
    const linkedEntityId = matchingWorkspace?.linked_entity_id || matchingWorkspace?.linked_entity?.id;
    const numericLinkedEntityId = Number(linkedEntityId);

    return Number.isInteger(numericLinkedEntityId) ? numericLinkedEntityId : null;
  }, [activeWorkspace, entityId]);

  const [entity, setEntity] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [income, setIncome] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [roles, setRoles] = useState([]);
  const [staff, setStaff] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [complianceDocuments, setComplianceDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    const loadEntityData = async () => {
      try {
        if (!entityId) {
          setLoading(false);
          return;
        }

        if (currentOrganization && entities.length === 0 && !didRequestEntitiesRef.current && fetchEntities) {
          didRequestEntitiesRef.current = true;
          await fetchEntities(currentOrganization.id);
        }

        // Find entity
        const foundEntity = entities.find((candidate) => String(candidate.id) === String(resolvedEntityId));
        if (!foundEntity) {
          setLoading(false);
          return;
        }

        setEntity(foundEntity);
        setLoading(false);

        // Load data asynchronously without blocking render
        setTimeout(async () => {
          try {
            // Load entity-specific financial data with timeout
            const financialPromise = Promise.race([
              Promise.all([
                fetchEntityExpenses(resolvedEntityId),
                fetchEntityIncome(resolvedEntityId),
                fetchEntityBudgets(resolvedEntityId)
              ]),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
            ]);

            const [entityExpenses, entityIncome, entityBudgets] = await financialPromise;
            setExpenses(entityExpenses || []);
            setIncome(entityIncome || []);
            setBudgets(entityBudgets || []);

            // Load entity management data with timeout
            const managementPromise = Promise.race([
              Promise.all([
                fetchEntityDepartments(resolvedEntityId),
                fetchEntityRoles(resolvedEntityId),
                fetchEntityStaff(resolvedEntityId),
                fetchEntityBankAccounts(resolvedEntityId),
                fetchEntityWallets(resolvedEntityId),
                fetchEntityComplianceDocuments(resolvedEntityId)
              ]),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
            ]);

            const [entityDepartments, entityRoles, entityStaff, entityBankAccounts, entityWallets, entityComplianceDocs] = await managementPromise;
            setDepartments(entityDepartments || []);
            setRoles(entityRoles || []);
            setStaff(entityStaff || []);
            setBankAccounts(entityBankAccounts || []);
            setWallets(entityWallets || []);
            setComplianceDocuments(entityComplianceDocs || []);
          } catch (err) {
            console.error('Failed to load entity data:', err);
            // Set empty arrays as fallback
            setExpenses([]);
            setIncome([]);
            setBudgets([]);
            setDepartments([]);
            setRoles([]);
            setStaff([]);
            setBankAccounts([]);
            setWallets([]);
            setComplianceDocuments([]);
          }
        }, 0);
      } catch (err) {
        console.error('Error in loadEntityData:', err);
        setLoading(false);
      }
    };

    loadEntityData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityId, entities, currentOrganization, fetchEntities, resolvedEntityId]);

  // Check if context is loaded
  if (!hasPermission || !PERMISSIONS) {
    return <div className="loading">Loading...</div>;
  }

  if (!hasPermission(PERMISSIONS.VIEW_ENTITIES)) {
    return <div className="permission-denied">You don't have permission to view entity dashboards.</div>;
  }

  if (loading) {
    return <div className="loading">Loading entity dashboard...</div>;
  }

  if (!entity) {
    return (
      <div className="error">
        <div>Entity Dashboard not found.</div>
        <button className="btn-primary btn-sm" onClick={() => navigate('/app/enterprise/entities')} style={{ marginTop: 12 }}>
          Back to Entities
        </button>
      </div>
    );
  }

  // Calculate financial metrics
  const totalExpenses = expenses.reduce((sum, exp) => sum + parseFloat(exp.amount), 0);
  const totalIncome = income.reduce((sum, inc) => sum + parseFloat(inc.amount), 0);
  const netIncome = totalIncome - totalExpenses;

  // Category breakdown for expenses
  const expenseCategories = expenses.reduce((acc, exp) => {
    const existing = acc.find(item => item.category === exp.category);
    if (existing) {
      existing.amount += parseFloat(exp.amount);
    } else {
      acc.push({ category: exp.category, amount: parseFloat(exp.amount) });
    }
    return acc;
  }, []);

  // Budget comparison
  const budgetComparison = budgets.map(budget => {
    const spent = expenses
      .filter(exp => exp.category === budget.category)
      .reduce((sum, exp) => sum + parseFloat(exp.amount), 0);

    return {
      category: budget.category,
      budget: parseFloat(budget.limit),
      spent: spent,
      remaining: parseFloat(budget.limit) - spent
    };
  });

  const COLORS = ['var(--color-error)', 'var(--color-cyan)', 'var(--color-cyan-dark)', 'var(--color-warning)', 'var(--color-success)'];

  return (
    <div className="ed-page">

      {/* Page Header */}
      <div className="ed-header">
        <div>
          <div className="ed-tab-subtitle" style={{ marginBottom: 6 }}>Entity Dashboard</div>
          <h1 className="ed-entity-name">{entity.name}</h1>
          <div className="ed-meta-row">
            {entity.country && <span className="ed-meta-item">{entity.country}</span>}
            {entity.entity_type && <><span className="ed-meta-sep">·</span><span className="ed-meta-item ed-meta-type">{entity.entity_type.replace(/_/g, ' ')}</span></>}
            <span className={`badge ${entity.status === 'active' ? 'active' : entity.status === 'dormant' ? 'dormant' : 'pending'}`}>
              {entity.status}
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="ed-tabs">
        {[
          { key: 'overview',     label: 'Overview' },
          { key: 'expenses',     label: `Expenses (${expenses.length})` },
          { key: 'income',       label: `Income (${income.length})` },
          { key: 'budgets',      label: `Budgets (${budgets.length})` },
          { key: 'staff',        label: `Staff & HR (${staff.length})` },
          { key: 'structure',    label: 'Company Structure' },
          { key: 'financial',    label: 'Financial Tracking' },
          { key: 'bookkeeping',  label: 'Bookkeeping' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`ed-tab-btn${activeTab === tab.key ? ' active' : ''}`}
          >{tab.label}</button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="ed-content">

        {/* ── OVERVIEW ── */}
        {activeTab === 'overview' && (
          <div>
            <div className="ed-section" style={{ marginBottom: 20 }}>
              <h2 className="ed-section-title">Overview</h2>
              <p className="ed-tab-subtitle">Snapshot of entity performance, cash position, and key operational areas.</p>
            </div>

            {/* Financial KPI cards */}
            <div className="summary-cards" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: 28 }}>
              <div className="summary-card income">
                <div className="card-label">Total Income</div>
                <div className="card-value">${totalIncome.toFixed(2)}</div>
                <div className="card-count">{income.length} transactions</div>
              </div>
              <div className="summary-card expense">
                <div className="card-label">Total Expenses</div>
                <div className="card-value">${totalExpenses.toFixed(2)}</div>
                <div className="card-count">{expenses.length} transactions</div>
              </div>
              <div className={`summary-card ${netIncome >= 0 ? 'profit' : 'expense'}`}>
                <div className="card-label">Net Income</div>
                <div className="card-value" style={{ color: netIncome >= 0 ? '#10B981' : '#DC2626' }}>${netIncome.toFixed(2)}</div>
                <div className="card-count">{totalIncome > 0 ? ((netIncome / totalIncome) * 100).toFixed(1) : 0}% margin</div>
              </div>
            </div>

            {/* Quick Access */}
            <div className="ed-section">
              <h2 className="ed-section-title">Quick Access</h2>
              <div className="ed-quick-access">
                {[
                  { label: 'Expenses',          count: expenses.length, action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/expenses`) },
                  { label: 'Income',             count: income.length,   action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/income`) },
                  { label: 'Budgets',            count: budgets.length,  action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/budgets`) },
                  { label: 'Bookkeeping',        action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/bookkeeping`) },
                  { label: 'Cashflow',           action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/cashflow-treasury`) },
                  { label: 'Staff & HR',         count: staff.length,    action: () => setActiveTab('staff') },
                  { label: 'Chart of Accounts',  action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/chart-of-accounts`) },
                  { label: 'General Ledger',     action: () => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/general-ledger`) },
                ].map((item, i) => (
                  <button key={i} onClick={item.action} className="ed-quick-card">
                    <div className="ed-quick-label">{item.label}</div>
                    {item.count !== undefined && <div className="ed-quick-count">{item.count}</div>}
                  </button>
                ))}
              </div>
            </div>

            {/* Charts */}
            <div className="chart-grid">
              <div className="chart-card">
                <h3>Expense Categories</h3>
                {expenseCategories.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={expenseCategories} dataKey="amount" nameKey="category" cx="50%" cy="50%" outerRadius={80}
                        label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}>
                        {expenseCategories.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => `$${v.toFixed(2)}`} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : <div className="empty-state"><p className="empty-state-text">No expense data available</p></div>}
              </div>
              <div className="chart-card">
                <h3>Budget vs Actual</h3>
                {budgetComparison.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={budgetComparison}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="category" />
                      <YAxis />
                      <Tooltip formatter={(v) => `$${v.toFixed(2)}`} />
                      <Legend />
                      <Bar dataKey="budget" fill="#10B981" name="Budget" />
                      <Bar dataKey="spent"  fill="#DC2626" name="Spent" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="empty-state"><p className="empty-state-text">No budget data available</p></div>}
              </div>
            </div>
          </div>
        )}

        {/* ── EXPENSES ── */}
        {activeTab === 'expenses' && (
          <div>
            <div className="ed-tab-header">
              <div>
                <h3 className="ed-tab-title">Expense Management</h3>
                <p className="ed-tab-subtitle">Track and manage all business expenses</p>
              </div>
              <button className="btn-primary btn-sm" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/expenses`)}>Open Manager →</button>
            </div>
            <div className="data-table-container">
              <table>
                <thead><tr><th>Date</th><th>Description</th><th>Category</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                <tbody>
                  {expenses.slice(0, 10).map(exp => (
                    <tr key={exp.id}>
                      <td className="table-row-muted">{new Date(exp.date).toLocaleDateString()}</td>
                      <td>{exp.description}</td>
                      <td className="table-row-muted">{exp.category}</td>
                      <td style={{ textAlign: 'right', fontWeight: 600, color: '#DC2626' }}>-${parseFloat(exp.amount).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {expenses.length === 0 && <div className="empty-state"><p className="empty-state-text">No expenses recorded</p></div>}
            </div>
          </div>
        )}

        {/* ── INCOME ── */}
        {activeTab === 'income' && (
          <div>
            <div className="ed-tab-header">
              <div>
                <h3 className="ed-tab-title">Income Management</h3>
                <p className="ed-tab-subtitle">Track revenue streams and analyze income sources</p>
              </div>
              <button className="btn-primary btn-sm" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/income`)}>Open Manager →</button>
            </div>
            <div className="data-table-container">
              <table>
                <thead><tr><th>Date</th><th>Source</th><th>Type</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                <tbody>
                  {income.slice(0, 10).map(inc => (
                    <tr key={inc.id}>
                      <td className="table-row-muted">{new Date(inc.date).toLocaleDateString()}</td>
                      <td>{inc.source}</td>
                      <td className="table-row-muted">{inc.income_type}</td>
                      <td style={{ textAlign: 'right', fontWeight: 600, color: '#10B981' }}>${parseFloat(inc.amount).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {income.length === 0 && <div className="empty-state"><p className="empty-state-text">No income recorded</p></div>}
            </div>
          </div>
        )}

        {/* ── BUDGETS ── */}
        {activeTab === 'budgets' && (
          <div>
            <div className="ed-tab-header">
              <div>
                <h3 className="ed-tab-title">Budget Management</h3>
                <p className="ed-tab-subtitle">Set spending limits and monitor utilization</p>
              </div>
              <button className="btn-primary btn-sm" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/budgets`)}>Open Manager →</button>
            </div>
            <div className="data-table-container">
              <table>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th style={{ textAlign: 'right' }}>Budget Limit</th>
                    <th style={{ textAlign: 'right' }}>Spent</th>
                    <th style={{ textAlign: 'right' }}>Remaining</th>
                    <th style={{ textAlign: 'center' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {budgets.map(budget => {
                    const spent = expenses.filter(e => e.category === budget.category).reduce((s, e) => s + parseFloat(e.amount), 0);
                    const remaining = parseFloat(budget.limit) - spent;
                    return (
                      <tr key={budget.id}>
                        <td style={{ fontWeight: 600 }}>{budget.category}</td>
                        <td style={{ textAlign: 'right' }}>${parseFloat(budget.limit).toFixed(2)}</td>
                        <td style={{ textAlign: 'right' }}>${spent.toFixed(2)}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600, color: remaining >= 0 ? '#10B981' : '#DC2626' }}>${remaining.toFixed(2)}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span className={`badge ${remaining >= 0 ? 'success' : 'error'}`}>{remaining >= 0 ? 'Under' : 'Over'}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {budgets.length === 0 && <div className="empty-state"><p className="empty-state-text">No budgets set</p></div>}
            </div>
          </div>
        )}

        {/* ── STAFF & HR ── */}
        {activeTab === 'staff' && (
          <div>
            <h3 className="ed-section-title">Staff & HR</h3>
            <div className="ed-staff-grid">
              <div className="chart-card">
                <h4 className="ed-card-h4">Departments ({departments.length})</h4>
                <div className="ed-scroll-list">
                  {departments.map(dept => (
                    <div key={dept.id} className="ed-list-item">
                      <div className="ed-list-name">{dept.name}</div>
                      <div className="ed-list-sub">{dept.staff_count} staff</div>
                    </div>
                  ))}
                  {departments.length === 0 && <p className="ed-list-empty">No departments</p>}
                </div>
              </div>
              <div className="chart-card">
                <h4 className="ed-card-h4">Roles ({roles.length})</h4>
                <div className="ed-scroll-list">
                  {roles.map(role => (
                    <div key={role.id} className="ed-list-item">
                      <div className="ed-list-name">{role.name}</div>
                      <div className="ed-list-sub">{role.staff_count} staff</div>
                    </div>
                  ))}
                  {roles.length === 0 && <p className="ed-list-empty">No roles</p>}
                </div>
              </div>
              <div className="chart-card">
                <h4 className="ed-card-h4">Quick Stats</h4>
                <div className="ed-stat-list">
                  <div className="ed-stat-row"><span className="ed-stat-key">Total Staff</span><span className="ed-stat-val">{staff.length}</span></div>
                  <div className="ed-stat-row"><span className="ed-stat-key">Active</span><span className="ed-stat-val ed-val-green">{staff.filter(s => s.status === 'active').length}</span></div>
                  <div className="ed-stat-row">
                    <span className="ed-stat-key">Avg Salary</span>
                    <span className="ed-stat-val">${(staff.filter(s => s.status === 'active').reduce((s, m) => s + (parseFloat(m.salary) || 0), 0) / Math.max(staff.filter(s => s.status === 'active').length, 1)).toFixed(0)}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="data-table-container">
              <table>
                <thead><tr><th>Name</th><th>Role</th><th>Department</th><th style={{ textAlign: 'center' }}>Status</th></tr></thead>
                <tbody>
                  {staff.slice(0, 10).map(member => (
                    <tr key={member.id}>
                      <td style={{ fontWeight: 500 }}>{member.full_name}</td>
                      <td className="table-row-muted">{member.role_name}</td>
                      <td className="table-row-muted">{member.department_name}</td>
                      <td style={{ textAlign: 'center' }}><span className={`badge ${member.status}`}>{member.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {staff.length === 0 && <div className="empty-state"><p className="empty-state-text">No staff added</p></div>}
            </div>
          </div>
        )}

        {/* ── COMPANY STRUCTURE ── */}
        {activeTab === 'structure' && (
          <div>
            <h3 className="ed-section-title">Company Structure</h3>
            <div className="ed-structure-grid">
              <div className="chart-card">
                <h4 className="ed-card-h4">Bank Accounts ({bankAccounts.length})</h4>
                <div className="ed-scroll-list">
                  {bankAccounts.map(acc => (
                    <div key={acc.id} className="ed-list-item">
                      <div className="ed-list-name">{acc.account_name}</div>
                      <div className="ed-list-sub">{acc.bank_name}</div>
                      <div className="ed-list-amount">${acc.balance.toFixed(2)}</div>
                    </div>
                  ))}
                  {bankAccounts.length === 0 && <p className="ed-list-empty">No bank accounts</p>}
                </div>
              </div>
              <div className="chart-card">
                <h4 className="ed-card-h4">Wallets ({wallets.length})</h4>
                <div className="ed-scroll-list">
                  {wallets.map(w => (
                    <div key={w.id} className="ed-list-item">
                      <div className="ed-list-name">{w.name}</div>
                      <div className="ed-list-sub">{w.get_wallet_type_display}</div>
                      <div className="ed-list-amount">${w.balance.toFixed(2)}</div>
                    </div>
                  ))}
                  {wallets.length === 0 && <p className="ed-list-empty">No wallets</p>}
                </div>
              </div>
              <div className="chart-card">
                <h4 className="ed-card-h4">Compliance Docs ({complianceDocuments.length})</h4>
                <div className="ed-scroll-list">
                  {complianceDocuments.map(doc => (
                    <div key={doc.id} className="ed-list-item">
                      <div className="ed-list-name">{doc.title}</div>
                      <div className={`ed-list-sub${doc.days_until_expiry <= 30 ? ' ed-expiring' : ''}`}>
                        Expires: {new Date(doc.expiry_date).toLocaleDateString()}
                      </div>
                      {doc.days_until_expiry !== null && doc.days_until_expiry <= 30 && (
                        <div className="ed-expiry-warning">{doc.days_until_expiry} days left</div>
                      )}
                    </div>
                  ))}
                  {complianceDocuments.length === 0 && <p className="ed-list-empty">No documents</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── FINANCIAL TRACKING ── */}
        {activeTab === 'financial' && (
          <div>
            <h3 className="ed-section-title">Financial Tracking</h3>
            <div className="chart-grid">
              <div className="chart-card">
                <h4 className="ed-card-h4">P&amp;L Summary</h4>
                <div className="ed-stat-list">
                  <div className="ed-stat-row"><span className="ed-stat-key">Total Revenue</span><span className="ed-stat-val ed-val-green">${totalIncome.toFixed(2)}</span></div>
                  <div className="ed-stat-row"><span className="ed-stat-key">Total Expenses</span><span className="ed-stat-val ed-val-red">-${totalExpenses.toFixed(2)}</span></div>
                  <div className="ed-stat-row ed-stat-row-total">
                    <span className="ed-stat-key" style={{ fontWeight: 700, color: '#111827' }}>Net Income</span>
                    <span className={`ed-stat-val ed-stat-lg ${netIncome >= 0 ? 'ed-val-green' : 'ed-val-red'}`}>${netIncome.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              <div className="chart-card">
                <h4 className="ed-card-h4">Cash Position</h4>
                <div className="ed-stat-list">
                  <div className="ed-stat-row"><span className="ed-stat-key">Bank Accounts</span><span className="ed-stat-val ed-val-blue">${bankAccounts.reduce((s, a) => s + parseFloat(a.balance), 0).toFixed(2)}</span></div>
                  <div className="ed-stat-row"><span className="ed-stat-key">Wallets</span><span className="ed-stat-val ed-val-blue">${wallets.reduce((s, w) => s + parseFloat(w.balance), 0).toFixed(2)}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── BOOKKEEPING ── */}
        {activeTab === 'bookkeeping' && (
          <div>
            <div className="chart-card" style={{ marginBottom: 18 }}>
              <h3 className="ed-tab-title" style={{ marginBottom: 6 }}>Bookkeeping Module</h3>
              <p className="ed-tab-subtitle">Manage financial transactions, chart of accounts, and reporting.</p>
              <div className="ed-bk-actions">
                <button className="btn-primary" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/bookkeeping`)}>Dashboard</button>
                <button className="btn-secondary" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/bookkeeping/transactions`)}>Transactions</button>
                <button className="btn-secondary" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/chart-of-accounts`)}>Chart of Accounts</button>
                <button className="btn-secondary" onClick={() => navigate(`/enterprise/entity/${resolvedEntityId || entityId}/general-ledger`)}>General Ledger</button>
              </div>
            </div>
            <div className="warning-banner">
              <strong>Note:</strong> Click any button above to access the full bookkeeping module with detailed transaction management and reporting tools.
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default EntityDashboard;
