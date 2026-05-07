import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Card, Modal, PageHeader, Table, Input } from '../../components/ui';
import { useEnterprise } from '../../context/EnterpriseContext';
import { automationArtifactsAPI, automationWorkflowsAPI } from '../../services/api';

const STATUS_COLORS = {
  completed: '#15803d',
  failed: '#dc2626',
  running: '#c2410c',
  pending: '#1d4ed8',
};

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
];

const REPORT_TYPE_OPTIONS = [
  { value: 'enterprise_reporting_pack', label: 'Enterprise Board Pack' },
  { value: 'compliance_reporting_pack', label: 'Compliance Board Pack' },
];

const EXPORT_FORMAT_OPTIONS = [
  { value: 'pdf', label: 'PDF' },
  { value: 'xlsx', label: 'XLSX' },
  { value: 'json', label: 'JSON' },
];

const TIMEZONE_GROUPS = [
  {
    label: 'North America',
    options: [
      { value: 'America/New_York', label: 'Eastern Time' },
      { value: 'America/Chicago', label: 'Central Time' },
      { value: 'America/Denver', label: 'Mountain Time' },
      { value: 'America/Los_Angeles', label: 'Pacific Time' },
      { value: 'America/Toronto', label: 'Toronto' },
    ],
  },
  {
    label: 'Latin America',
    options: [
      { value: 'America/Sao_Paulo', label: 'Sao Paulo' },
    ],
  },
  {
    label: 'Europe',
    options: [
      { value: 'UTC', label: 'UTC' },
      { value: 'Europe/London', label: 'London' },
      { value: 'Europe/Dublin', label: 'Dublin' },
      { value: 'Europe/Berlin', label: 'Berlin' },
      { value: 'Europe/Paris', label: 'Paris' },
      { value: 'Europe/Zurich', label: 'Zurich' },
    ],
  },
  {
    label: 'Middle East and Asia',
    options: [
      { value: 'Asia/Dubai', label: 'Dubai' },
      { value: 'Asia/Singapore', label: 'Singapore' },
      { value: 'Asia/Hong_Kong', label: 'Hong Kong' },
      { value: 'Asia/Tokyo', label: 'Tokyo' },
    ],
  },
  {
    label: 'Australia',
    options: [
      { value: 'Australia/Sydney', label: 'Sydney' },
    ],
  },
];

const PRESET_TIMEZONE_VALUES = TIMEZONE_GROUPS.flatMap((group) => group.options.map((option) => option.value));

const getDefaultScheduleTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch (error) {
    return 'UTC';
  }
};

const BLANK_FORM = {
  name: '',
  description: '',
  entity: '',
  frequency: 'monthly',
  next_run_at: '',
  schedule_timezone: 'UTC',
  report_type: 'enterprise_reporting_pack',
  export_format: 'pdf',
  months_back: '12',
  retention_days: '90',
  recipients: '',
  subject: '',
  is_active: true,
};

const formatDateTime = (value, timeZone) => {
  if (!value) return '—';
  const date = new Date(value);
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timeZone || undefined,
  }).format(date);
};

const formatBytes = (value) => {
  if (!value) return '0 B';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

const resolveTimezonePresetValue = (timeZone) => (PRESET_TIMEZONE_VALUES.includes(timeZone) ? timeZone : '__custom__');

const toDateTimeLocal = (value) => {
  if (!value) return '';
  const date = new Date(value);
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
};

const parseRecipients = (value) => value
  .split(/[\n,;]/)
  .map((item) => item.trim())
  .filter(Boolean);

const formatRecipients = (recipients) => (recipients || []).join(', ');

const workflowToForm = (workflow) => {
  const action = workflow.actions?.[0] || {};
  return {
    name: workflow.name || '',
    description: workflow.description || '',
    entity: workflow.entity || '',
    frequency: workflow.trigger_config?.frequency || 'monthly',
    next_run_at: toDateTimeLocal(workflow.trigger_config?.next_run_at || ''),
    schedule_timezone: workflow.trigger_config?.schedule_timezone || 'UTC',
    report_type: action.type || 'enterprise_reporting_pack',
    export_format: action.format || 'pdf',
    months_back: String(action.months_back || 12),
    retention_days: String(workflow.trigger_config?.retention_days || 90),
    recipients: formatRecipients(action.recipients),
    subject: action.subject || '',
    is_active: Boolean(workflow.is_active),
  };
};

const formToPayload = (form, organizationId) => {
  const nextRunIso = form.next_run_at ? new Date(form.next_run_at).toISOString() : new Date().toISOString();
  return {
    organization: organizationId,
    entity: form.entity || null,
    name: form.name.trim(),
    description: form.description.trim(),
    trigger_type: 'schedule',
    trigger_config: {
      frequency: form.frequency,
      next_run_at: nextRunIso,
      schedule_timezone: form.schedule_timezone || 'UTC',
      retention_days: Number(form.retention_days || 90),
    },
    actions: [
      {
        type: form.report_type,
        format: form.export_format,
        months_back: Number(form.months_back || 12),
        recipients: parseRecipients(form.recipients),
        subject: form.subject.trim(),
      },
    ],
    is_active: Boolean(form.is_active),
  };
};

export default function AutomationRules() {
  const { currentOrganization, entities } = useEnterprise();
  const [workflows, setWorkflows] = useState([]);
  const [cleanupImpact, setCleanupImpact] = useState({ summary: {}, workflows: [], days_ahead: 30 });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  const [form, setForm] = useState(BLANK_FORM);
  const [busyWorkflowId, setBusyWorkflowId] = useState(null);

  const loadAutomationData = useCallback(async () => {
    if (!currentOrganization?.id) {
      setWorkflows([]);
      setCleanupImpact({ summary: {}, workflows: [], days_ahead: 30 });
      return;
    }

    setLoading(true);
    try {
      const [workflowResponse, cleanupResponse] = await Promise.all([
        automationWorkflowsAPI.getAll({ organization: currentOrganization.id }),
        automationWorkflowsAPI.cleanupImpact({ organization: currentOrganization.id, days_ahead: 30 }),
      ]);
      setWorkflows(workflowResponse.data.results || workflowResponse.data || []);
      setCleanupImpact(cleanupResponse.data || { summary: {}, workflows: [], days_ahead: 30 });
      setError('');
    } catch (requestError) {
      console.error('Failed to load automation data', requestError);
      setError(requestError.response?.data?.detail || 'Failed to load automation workflows.');
      setWorkflows([]);
      setCleanupImpact({ summary: {}, workflows: [], days_ahead: 30 });
    } finally {
      setLoading(false);
    }
  }, [currentOrganization?.id]);

  useEffect(() => {
    loadAutomationData();
  }, [loadAutomationData]);

  const stats = useMemo(() => {
    const now = new Date();
    const allExecutions = workflows.flatMap((workflow) => workflow.executions || []);
    const allArtifacts = allExecutions.flatMap((execution) => execution.artifacts || []);
    const dueNow = workflows.filter((workflow) => {
      const nextRun = workflow.trigger_config?.next_run_at;
      return workflow.is_active && nextRun && new Date(nextRun) <= now;
    }).length;
    return [
      { label: 'Active Workflows', value: workflows.filter((workflow) => workflow.is_active).length, accent: '#15803d' },
      { label: 'Due Now', value: dueNow, accent: '#c2410c' },
      { label: 'Expiring Soon', value: cleanupImpact.summary?.artifacts_expiring || 0, accent: '#b45309' },
      { label: 'Artifacts Stored', value: allArtifacts.length, accent: '#1d4ed8' },
    ];
  }, [cleanupImpact.summary, workflows]);

  const recentExecutions = useMemo(() => workflows
    .flatMap((workflow) => (workflow.executions || []).map((execution) => ({
      ...execution,
      workflow_name: workflow.name,
      workflow_id: workflow.id,
    })))
    .sort((left, right) => new Date(right.triggered_at || 0) - new Date(left.triggered_at || 0))
    .slice(0, 8), [workflows]);

  const recentArtifacts = useMemo(() => workflows
    .flatMap((workflow) => (workflow.executions || []).flatMap((execution) =>
      (execution.artifacts || []).map((artifact) => ({
        ...artifact,
        workflow_name: workflow.name,
        execution_triggered_at: execution.triggered_at,
      }))
    ))
    .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))
    .slice(0, 12), [workflows]);

  const entityOptions = useMemo(
    () => (entities || []).filter((entity) => String(entity.organization) === String(currentOrganization?.id)),
    [entities, currentOrganization?.id]
  );

  const openCreateModal = () => {
    setEditingWorkflow(null);
    setForm({ ...BLANK_FORM, schedule_timezone: getDefaultScheduleTimezone() });
    setShowModal(true);
    setError('');
  };

  const openEditModal = (workflow) => {
    setEditingWorkflow(workflow);
    setForm(workflowToForm(workflow));
    setShowModal(true);
    setError('');
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingWorkflow(null);
    setForm(BLANK_FORM);
  };

  const handleSave = async () => {
    if (!currentOrganization?.id) {
      setError('Select an organization before creating automation workflows.');
      return;
    }
    if (!form.name.trim()) {
      setError('Workflow name is required.');
      return;
    }
    if (!parseRecipients(form.recipients).length) {
      setError('At least one recipient email is required.');
      return;
    }
    if (!form.schedule_timezone.trim()) {
      setError('A schedule timezone is required.');
      return;
    }

    setSaving(true);
    try {
      const payload = formToPayload(form, currentOrganization.id);
      if (editingWorkflow) {
        await automationWorkflowsAPI.update(editingWorkflow.id, payload);
      } else {
        await automationWorkflowsAPI.create(payload);
      }
      closeModal();
      await loadAutomationData();
    } catch (requestError) {
      console.error('Failed to save workflow', requestError);
      const data = requestError.response?.data;
      setError(data ? Object.entries(data).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' | ') : 'Failed to save workflow.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (workflowId) => {
    if (!window.confirm('Delete this automation workflow?')) return;
    try {
      await automationWorkflowsAPI.delete(workflowId);
      await loadAutomationData();
    } catch (requestError) {
      console.error('Failed to delete workflow', requestError);
      setError(requestError.response?.data?.detail || 'Failed to delete workflow.');
    }
  };

  const handleExecute = async (workflowId) => {
    setBusyWorkflowId(workflowId);
    try {
      await automationWorkflowsAPI.execute(workflowId);
      await loadAutomationData();
    } catch (requestError) {
      console.error('Failed to execute workflow', requestError);
      setError(requestError.response?.data?.detail || 'Failed to execute workflow.');
    } finally {
      setBusyWorkflowId(null);
    }
  };

  const handleRunDue = async () => {
    setBusyWorkflowId('run-due');
    try {
      await automationWorkflowsAPI.runDue();
      await loadAutomationData();
    } catch (requestError) {
      console.error('Failed to run due workflows', requestError);
      setError(requestError.response?.data?.detail || 'Failed to run due workflows.');
    } finally {
      setBusyWorkflowId(null);
    }
  };

  const handleDownloadArtifact = async (artifact) => {
    try {
      const response = await automationArtifactsAPI.download(artifact.id);
      const blob = new Blob([response.data], {
        type: response.headers?.['content-type'] || 'application/octet-stream',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = artifact.file_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      console.error('Failed to download artifact', requestError);
      setError(requestError.response?.data?.detail || 'Failed to download artifact.');
    }
  };

  const workflowColumns = [
    { key: 'name', header: 'Workflow', render: (_, row) => <strong>{row.name}</strong> },
    {
      key: 'frequency',
      header: 'Cadence',
      render: (_, row) => `${row.trigger_config?.frequency || '—'} · ${row.trigger_config?.schedule_timezone || 'UTC'}`,
    },
    { key: 'recipients', header: 'Recipients', render: (_, row) => formatRecipients(row.actions?.[0]?.recipients).slice(0, 48) || '—' },
    { key: 'export_format', header: 'Format', render: (_, row) => (row.actions?.[0]?.format || 'pdf').toUpperCase() },
    {
      key: 'next_run_at',
      header: 'Next Run',
      render: (_, row) => formatDateTime(row.trigger_config?.next_run_at, row.trigger_config?.schedule_timezone),
    },
    {
      key: 'last_execution',
      header: 'Last Status',
      render: (_, row) => {
        const status = row.executions?.[0]?.status || 'pending';
        return <span style={{ color: STATUS_COLORS[status] || '#475569', fontWeight: 700, textTransform: 'capitalize' }}>{status}</span>;
      },
    },
  ];

  const executionColumns = [
    { key: 'workflow_name', header: 'Workflow' },
    { key: 'triggered_at', header: 'Triggered', render: (value) => formatDateTime(value) },
    {
      key: 'status',
      header: 'Status',
      render: (value) => <span style={{ color: STATUS_COLORS[value] || '#475569', fontWeight: 700, textTransform: 'capitalize' }}>{value}</span>,
    },
    { key: 'artifact_count', header: 'Artifacts', render: (_, row) => row.artifacts?.length || 0 },
  ];

  const artifactColumns = [
    { key: 'workflow_name', header: 'Workflow' },
    { key: 'file_name', header: 'Artifact' },
    { key: 'export_format', header: 'Format', render: (value) => String(value || '').toUpperCase() },
    { key: 'created_at', header: 'Generated', render: (value) => formatDateTime(value) },
  ];

  const cleanupColumns = [
    { key: 'workflow_name', header: 'Workflow' },
    { key: 'entity_name', header: 'Scope' },
    { key: 'retention_days', header: 'Retention', render: (value) => `${value} days` },
    { key: 'total_artifacts', header: 'Stored' },
    {
      key: 'artifacts_expiring_within_window',
      header: `Expiring In ${cleanupImpact.days_ahead || 30}d`,
      render: (value, row) => (
        <span style={{ color: row.artifacts_already_expired ? '#dc2626' : value ? '#b45309' : '#475569', fontWeight: 700 }}>
          {value}
        </span>
      ),
    },
    {
      key: 'bytes_expiring_within_window',
      header: 'Bytes At Risk',
      render: (value) => formatBytes(value),
    },
    {
      key: 'next_expiration_at',
      header: 'Next Cleanup',
      render: (value, row) => formatDateTime(value, row.schedule_timezone),
    },
  ];

  return (
    <div className="module-page">
      <PageHeader
        title="Automation Rules"
        subtitle="Schedule enterprise and compliance board packs with cadence, recipients, export format, and retained artifact history."
        actions={(
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="secondary" size="small" onClick={handleRunDue} disabled={busyWorkflowId === 'run-due' || !currentOrganization?.id}>
              {busyWorkflowId === 'run-due' ? 'Running…' : 'Run Due Now'}
            </Button>
            <Button variant="primary" size="small" onClick={openCreateModal} disabled={!currentOrganization?.id}>New Workflow</Button>
          </div>
        )}
      />

      {error && <div className="error-banner" style={{ background: '#fef2f2', border: '1px solid #fca5a5', padding: '10px 16px', borderRadius: 8, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>{error}</div>}

      <div className="stats-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card" style={{ background: 'var(--color-white)', border: '1px solid var(--border-color-default)', borderTop: `3px solid ${stat.accent}`, borderRadius: 8, padding: '16px 20px' }}>
            <div style={{ fontSize: 12, color: 'var(--color-silver-dark)', marginBottom: 4 }}>{stat.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: stat.accent }}>{stat.value}</div>
          </div>
        ))}
      </div>

      <Card>
        {loading ? <div style={{ textAlign: 'center', padding: 32, color: 'var(--color-silver-dark)' }}>Loading workflows…</div> : workflows.length === 0 ? <div style={{ textAlign: 'center', padding: 32, color: 'var(--color-silver-dark)' }}>No scheduled reporting workflows yet.</div> : (
          <Table
            columns={workflowColumns}
            data={workflows}
            actions={(row) => (
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => openEditModal(row)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, border: '1px solid var(--border-color-default)', cursor: 'pointer', background: 'transparent' }}>Edit</button>
                <button onClick={() => handleExecute(row.id)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, border: '1px solid var(--border-color-default)', cursor: 'pointer', background: 'transparent' }} disabled={busyWorkflowId === row.id}>{busyWorkflowId === row.id ? 'Running…' : 'Run'}</button>
                <button onClick={() => handleDelete(row.id)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, border: '1px solid #fca5a5', cursor: 'pointer', background: 'transparent', color: '#dc2626' }}>Delete</button>
              </div>
            )}
          />
        )}
      </Card>

      <Card style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16 }}>
          <h3 style={{ marginTop: 0, marginBottom: 12 }}>Cleanup Exposure</h3>
          <div style={{ fontSize: 12, color: 'var(--color-silver-dark)' }}>
            {cleanupImpact.summary?.artifacts_expiring || 0} artifacts and {formatBytes(cleanupImpact.summary?.bytes_expiring || 0)} due within the next {cleanupImpact.days_ahead || 30} days
          </div>
        </div>
        {loading ? <div style={{ color: 'var(--color-silver-dark)', padding: '12px 0' }}>Loading cleanup exposure…</div> : cleanupImpact.workflows.length === 0 ? <div style={{ color: 'var(--color-silver-dark)', padding: '12px 0' }}>No workflows available for cleanup forecasting.</div> : <Table columns={cleanupColumns} data={cleanupImpact.workflows} />}
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 16, marginTop: 24 }}>
        <Card>
          <h3 style={{ marginTop: 0 }}>Recent Executions</h3>
          {recentExecutions.length === 0 ? <div style={{ color: 'var(--color-silver-dark)', padding: '12px 0' }}>No executions yet.</div> : <Table columns={executionColumns} data={recentExecutions} />}
        </Card>
        <Card>
          <h3 style={{ marginTop: 0 }}>Artifact History</h3>
          {recentArtifacts.length === 0 ? <div style={{ color: 'var(--color-silver-dark)', padding: '12px 0' }}>No artifacts stored yet.</div> : (
            <Table
              columns={artifactColumns}
              data={recentArtifacts}
              actions={(row) => (
                <button onClick={() => handleDownloadArtifact(row)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, border: '1px solid var(--border-color-default)', cursor: 'pointer', background: 'transparent' }}>Download</button>
              )}
            />
          )}
        </Card>
      </div>

      <Modal
        isOpen={showModal}
        onClose={closeModal}
        title={editingWorkflow ? 'Edit Reporting Workflow' : 'New Reporting Workflow'}
        footer={(
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving…' : editingWorkflow ? 'Save Workflow' : 'Create Workflow'}</Button>
          </>
        )}
      >
        <Input label="Workflow Name" required value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Monthly board pack" />
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Description</label>
          <textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows={3} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13, resize: 'vertical' }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Entity Scope</label>
            <select value={form.entity} onChange={(event) => setForm((current) => ({ ...current, entity: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }}>
              <option value="">All organization entities</option>
              {entityOptions.map((entity) => <option key={entity.id} value={entity.id}>{entity.name}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Cadence</label>
            <select value={form.frequency} onChange={(event) => setForm((current) => ({ ...current, frequency: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }}>
              {FREQUENCY_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Next Run</label>
            <input type="datetime-local" value={form.next_run_at} onChange={(event) => setForm((current) => ({ ...current, next_run_at: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Schedule Timezone</label>
            <select
              value={resolveTimezonePresetValue(form.schedule_timezone)}
              onChange={(event) => {
                const selectedValue = event.target.value;
                setForm((current) => ({
                  ...current,
                  schedule_timezone: selectedValue === '__custom__'
                    ? (PRESET_TIMEZONE_VALUES.includes(current.schedule_timezone) ? getDefaultScheduleTimezone() : current.schedule_timezone)
                    : selectedValue,
                }));
              }}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }}
            >
              {TIMEZONE_GROUPS.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.options.map((option) => <option key={option.value} value={option.value}>{option.label} · {option.value}</option>)}
                </optgroup>
              ))}
              <option value="__custom__">Custom timezone…</option>
            </select>
            {resolveTimezonePresetValue(form.schedule_timezone) === '__custom__' && (
              <input
                value={form.schedule_timezone}
                onChange={(event) => setForm((current) => ({ ...current, schedule_timezone: event.target.value }))}
                placeholder="Africa/Johannesburg"
                style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13, marginTop: 8 }}
              />
            )}
            <div style={{ fontSize: 11, color: 'var(--color-silver-dark)', marginTop: 4 }}>
              Next run times and cleanup forecasts are shown in this workflow timezone.
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Reporting Window (Months)</label>
            <input type="number" min="1" max="36" value={form.months_back} onChange={(event) => setForm((current) => ({ ...current, months_back: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Artifact Retention (Days)</label>
            <input type="number" min="1" max="3650" value={form.retention_days} onChange={(event) => setForm((current) => ({ ...current, retention_days: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Report Pack</label>
            <select value={form.report_type} onChange={(event) => setForm((current) => ({ ...current, report_type: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }}>
              {REPORT_TYPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Export Format</label>
            <select value={form.export_format} onChange={(event) => setForm((current) => ({ ...current, export_format: event.target.value }))} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13 }}>
              {EXPORT_FORMAT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
        </div>
        <Input label="Email Subject" value={form.subject} onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))} placeholder="Ledgora monthly board pack" />
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Recipients</label>
          <textarea value={form.recipients} onChange={(event) => setForm((current) => ({ ...current, recipients: event.target.value }))} rows={3} placeholder="cfo@example.com, controller@example.com" style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border-color-default)', borderRadius: 6, fontSize: 13, resize: 'vertical' }} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, marginTop: 8 }}>
          <input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} />
          Workflow is active
        </label>
      </Modal>
    </div>
  );
}
