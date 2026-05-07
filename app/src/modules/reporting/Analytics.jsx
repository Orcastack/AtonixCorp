import React, { useState } from 'react';
import { PageHeader, Card, Button, Modal, Input } from '../../components/ui';

const reports = [
  { id: 1,  title: 'Income Statement',      desc: 'Revenue, expenses, and net income by period',          category: 'Financials',   runs: 45 },
  { id: 2,  title: 'Balance Sheet',          desc: 'Assets, liabilities, and equity snapshot',             category: 'Financials',   runs: 38 },
  { id: 3,  title: 'Cash Flow Statement',    desc: 'Operating, investing, and financing cash flows',       category: 'Financials',   runs: 32 },
  { id: 4,  title: 'AR Aging Report',        desc: 'Outstanding receivables by age bucket',                category: 'Subledger',    runs: 28 },
  { id: 5,  title: 'AP Aging Report',        desc: 'Outstanding payables by age bucket',                   category: 'Subledger',    runs: 22 },
  { id: 6,  title: 'Fixed Asset Schedule',   desc: 'Depreciation schedule for all fixed assets',          category: 'Subledger',    runs: 15 },
  { id: 7,  title: 'Payroll Summary',        desc: 'Gross pay, deductions, and net pay by period',        category: 'HR & Payroll', runs: 12 },
  { id: 8,  title: 'Budget vs Actual',       desc: 'Variance analysis against approved budget',           category: 'Budgeting',    runs: 24 },
  { id: 9,  title: 'Tax Liability Report',   desc: 'Detailed breakdown of tax liabilities by jurisdiction',category: 'Tax',          runs: 8  },
  { id: 10, title: 'General Ledger Detail',  desc: 'All GL transactions by account and date range',       category: 'Accounting',   runs: 35 },
  { id: 11, title: 'Journal Entry Summary',  desc: 'All journal entries by period with audit trail',      category: 'Accounting',   runs: 29 },
  { id: 12, title: 'Inventory Valuation',    desc: 'FIFO/LIFO/Average cost inventory report',             category: 'Inventory',    runs: 10 },
];

const recentRuns = [
  { report: 'Income Statement',    user: 'sarah.johnson@ledgora.com',  date: '2025-01-31', format: 'PDF',  status: 'Complete' },
  { report: 'AR Aging Report',     user: 'michael.chen@ledgora.com',   date: '2025-01-31', format: 'CSV',  status: 'Complete' },
  { report: 'Budget vs Actual',    user: 'admin@ledgora.com',          date: '2025-01-30', format: 'XLSX', status: 'Complete' },
  { report: 'General Ledger',      user: 'sarah.johnson@ledgora.com',  date: '2025-01-30', format: 'CSV',  status: 'Complete' },
  { report: 'Tax Liability Report',user: 'michael.chen@ledgora.com',   date: '2025-01-29', format: 'PDF',  status: 'Error'    },
];

const CATEGORY_COLORS = {
  Financials:   'var(--color-cyan)',
  Subledger:    'var(--color-success)',
  'HR & Payroll': 'var(--color-warning)',
  Budgeting:    'var(--color-cyan-dark)',
  Tax:          'var(--color-error)',
  Accounting:   'var(--color-midnight)',
  Inventory:    'var(--color-cyan-dark)',
};

const STATUS_COLORS = { Complete: 'var(--color-success)', Error: 'var(--color-error)', Running: 'var(--color-warning)' };

const BLANK_RUN = { report: '', dateFrom: '', dateTo: '', format: 'PDF', entity: 'all' };

export default function Analytics() {
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [form, setForm] = useState(BLANK_RUN);
  const set = f => e => setForm(p => ({ ...p, [f]: e.target.value }));

  const filtered = search
    ? reports.filter(r =>
        r.title.toLowerCase().includes(search.toLowerCase()) ||
        r.category.toLowerCase().includes(search.toLowerCase()) ||
        r.desc.toLowerCase().includes(search.toLowerCase()))
    : reports;

  const categories = [...new Set(filtered.map(r => r.category))];
  const totalRuns = reports.reduce((s, r) => s + r.runs, 0);

  const openRunModal = (report) => {
    setSelectedReport(report);
    setForm(f => ({ ...f, report: report.title }));
    setShowModal(true);
  };

  const handleRun = () => { setForm(BLANK_RUN); setSelectedReport(null); setShowModal(false); };

  return (
    <div className="module-page">
      <PageHeader
        title="Reports & Analytics"
        subtitle="Access and run all pre-built financial reports"
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="secondary" size="small">Scheduled Reports</Button>
            <Button variant="primary" size="small" onClick={() => { setSelectedReport(null); setShowModal(true); }}>Run Report</Button>
          </div>
        }
      />

      <div className="stats-row">
        <Card className="stat-card">
          <div className="stat-label">Available Reports</div>
          <div className="stat-value">{reports.length}</div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">Total Runs (MTD)</div>
          <div className="stat-value">{totalRuns}</div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">Scheduled Reports</div>
          <div className="stat-value">3</div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">Last Export</div>
          <div className="stat-value" style={{ fontSize: 14 }}>Jan 31</div>
        </Card>
      </div>

      <Card style={{ marginBottom: 20 }}>
        <Input
          placeholder="Search reports by name or category…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ maxWidth: 420 }}
        />
      </Card>

      {categories.length === 0 ? (
        <Card>
          <p style={{ textAlign: 'center', color: 'var(--color-silver-dark)', padding: '32px 0' }}>
            No reports match &ldquo;{search}&rdquo;
          </p>
        </Card>
      ) : categories.map(cat => (
        <div key={cat} style={{ marginBottom: 28 }}>
          <h3 style={{
            fontSize: 13, fontWeight: 700, color: CATEGORY_COLORS[cat] || 'var(--color-cyan)',
            textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 12,
            paddingBottom: 8, borderBottom: `2px solid ${CATEGORY_COLORS[cat] || 'var(--color-cyan)'}`,
          }}>{cat}</h3>
          <div className="report-grid">
            {filtered.filter(r => r.category === cat).map(r => (
              <div key={r.id} className="report-card-link" onClick={() => openRunModal(r)} style={{ cursor: 'pointer' }}>
                <div className="report-card-title">{r.title}</div>
                <div className="report-card-desc">{r.desc}</div>
                <div style={{ marginTop: 8, fontSize: 11, color: 'var(--color-silver-dark)', fontWeight: 600 }}>
                  {r.runs} runs this month
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <Card title="Recent Report Runs" style={{ marginTop: 8 }}>
        <table className="risk-table">
          <thead>
            <tr>
              <th>Report</th><th>Run By</th><th>Date</th><th>Format</th><th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.map((r, i) => (
              <tr key={i}>
                <td><strong>{r.report}</strong></td>
                <td style={{ color: 'var(--color-silver-dark)' }}>{r.user}</td>
                <td>{r.date}</td>
                <td><code style={{ fontSize: 12 }}>{r.format}</code></td>
                <td><span className="status-badge" style={{ background: STATUS_COLORS[r.status] }}>{r.status}</span></td>
                <td><Button variant="secondary" size="small">Download</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Modal
        isOpen={showModal}
        onClose={() => { setShowModal(false); setForm(BLANK_RUN); }}
        title={selectedReport ? `Run: ${selectedReport.title}` : 'Run Report'}
      >
        <div className="form-grid">
          {!selectedReport && (
            <div style={{ gridColumn: '1 / -1' }}>
              <label className="input-label">Report</label>
              <select className="filter-select" style={{ width: '100%', height: 40 }} value={form.report} onChange={set('report')}>
                <option value="">Select a report…</option>
                {reports.map(r => <option key={r.id} value={r.title}>{r.title}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="input-label">Date From</label>
            <Input type="date" value={form.dateFrom} onChange={set('dateFrom')} />
          </div>
          <div>
            <label className="input-label">Date To</label>
            <Input type="date" value={form.dateTo} onChange={set('dateTo')} />
          </div>
          <div>
            <label className="input-label">Export Format</label>
            <select className="filter-select" style={{ width: '100%', height: 40 }} value={form.format} onChange={set('format')}>
              <option value="PDF">PDF</option>
              <option value="CSV">CSV</option>
              <option value="XLSX">XLSX</option>
            </select>
          </div>
          <div>
            <label className="input-label">Entity</label>
            <select className="filter-select" style={{ width: '100%', height: 40 }} value={form.entity} onChange={set('entity')}>
              <option value="all">All Entities</option>
              <option value="1">Ledgora US</option>
              <option value="2">Ledgora UK</option>
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <Button variant="secondary" onClick={() => { setShowModal(false); setForm(BLANK_RUN); }}>Cancel</Button>
          <Button variant="primary" onClick={handleRun} disabled={!selectedReport && !form.report}>Generate Report</Button>
        </div>
      </Modal>
    </div>
  );
}
