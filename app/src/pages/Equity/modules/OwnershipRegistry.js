import React, { useMemo, useState } from 'react';
import EquityCrudModuleScreen from '../components/EquityCrudModuleScreen';
import { useEquity } from '../../../context/EquityContext';

const EMPTY_FORM = {
  name: '',
  shareholder_type: 'individual',
  email: '',
  beneficial_owner: false,
  voting_rights_percent: '0',
  kyc_status: 'pending',
  aml_status: 'pending',
  notes: '',
};

const EMPTY_HOLDING_FORM = {
  shareholder: '',
  share_class: '',
  quantity: '0',
  diluted_quantity: '0',
  issue_price_per_share: '0',
  invested_amount: '0',
  pro_rata_eligible: false,
  pro_rata_take_up_percent: '100',
  issued_at: '',
};

const OwnershipRegistry = () => {
  const {
    shareholders,
    holdings,
    shareClasses,
    summary,
    loading,
    error,
    saving,
    createShareholder,
    updateShareholder,
    deleteShareholder,
    createHolding,
    updateHolding,
    deleteHolding,
  } = useEquity();
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [holdingForm, setHoldingForm] = useState(EMPTY_HOLDING_FORM);
  const [editingHoldingId, setEditingHoldingId] = useState(null);

  const metrics = useMemo(() => ([
    { label: 'Registered holders', value: summary.totalShareholders, note: 'Individuals, entities, employees, and investors' },
    { label: 'Beneficial owners', value: shareholders.filter((item) => item.beneficial_owner).length, note: 'Ultimate ownership disclosures tracked' },
    { label: 'Voting positions', value: holdings.length, note: 'Recorded positions with voting rights history' },
  ]), [holdings.length, shareholders, summary.totalShareholders]);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const resetHoldingForm = () => {
    setHoldingForm(EMPTY_HOLDING_FORM);
    setEditingHoldingId(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      voting_rights_percent: Number(form.voting_rights_percent || 0),
    };

    if (editingId) {
      await updateShareholder(editingId, payload);
    } else {
      await createShareholder(payload);
    }
    resetForm();
  };

  const handleEdit = (record) => {
    setEditingId(record.id);
    setForm({
      name: record.name || '',
      shareholder_type: record.shareholder_type || 'individual',
      email: record.email || '',
      beneficial_owner: Boolean(record.beneficial_owner),
      voting_rights_percent: String(record.voting_rights_percent ?? '0'),
      kyc_status: record.kyc_status || 'pending',
      aml_status: record.aml_status || 'pending',
      notes: record.notes || '',
    });
  };

  const handleDelete = async (record) => {
    await deleteShareholder(record.id);
    if (editingId === record.id) {
      resetForm();
    }
  };

  const handleHoldingSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      ...holdingForm,
      quantity: Number(holdingForm.quantity || 0),
      diluted_quantity: Number(holdingForm.diluted_quantity || 0),
      issue_price_per_share: Number(holdingForm.issue_price_per_share || 0),
      invested_amount: Number(holdingForm.invested_amount || 0),
      pro_rata_take_up_percent: Number(holdingForm.pro_rata_take_up_percent || 0),
    };
    if (editingHoldingId) {
      await updateHolding(editingHoldingId, payload);
    } else {
      await createHolding(payload);
    }
    resetHoldingForm();
  };

  const handleHoldingEdit = (record) => {
    setEditingHoldingId(record.id);
    setHoldingForm({
      shareholder: record.shareholder || '',
      share_class: record.share_class || '',
      quantity: String(record.quantity ?? 0),
      diluted_quantity: String(record.diluted_quantity ?? 0),
      issue_price_per_share: String(record.issue_price_per_share ?? 0),
      invested_amount: String(record.invested_amount ?? 0),
      pro_rata_eligible: Boolean(record.pro_rata_eligible),
      pro_rata_take_up_percent: String(record.pro_rata_take_up_percent ?? 100),
      issued_at: record.issued_at || '',
    });
  };

  const handleHoldingDelete = async (record) => {
    await deleteHolding(record.id);
    if (editingHoldingId === record.id) {
      resetHoldingForm();
    }
  };

  return (
    <>
      <EquityCrudModuleScreen
        title="Ownership Registry"
        description="Maintain a compliance-grade register of shareholders, beneficial owners, voting rights, and KYC or AML posture."
        metrics={metrics}
        records={shareholders}
        columns={[
          { key: 'name', label: 'Shareholder' },
          { key: 'shareholder_type', label: 'Type' },
          { key: 'email', label: 'Contact' },
          { key: 'kyc_status', label: 'KYC' },
          { key: 'aml_status', label: 'AML' },
          { key: 'voting_rights_percent', label: 'Voting %' },
        ]}
        emptyTitle="No shareholders have been registered yet"
        emptyBody="Create the first holder record to start the beneficial ownership registry and compliance workflow."
        formTitle="Create shareholder"
        formDescription="Capture the legal owner, beneficial owner designation, and onboarding status used throughout Ledgora Equity Management."
        formFields={[
          { key: 'name', label: 'Shareholder name', placeholder: 'Ada Ventures SPV' },
          {
            key: 'shareholder_type',
            label: 'Holder type',
            type: 'select',
            options: [
              { value: 'individual', label: 'Individual' },
              { value: 'entity', label: 'Entity' },
              { value: 'employee', label: 'Employee' },
              { value: 'investor', label: 'Investor' },
            ],
          },
          { key: 'email', label: 'Contact email', type: 'email', placeholder: 'owner@example.com' },
          { key: 'voting_rights_percent', label: 'Voting rights %', type: 'number', min: '0', step: '0.01' },
          { key: 'kyc_status', label: 'KYC status', placeholder: 'pending' },
          { key: 'aml_status', label: 'AML status', placeholder: 'pending' },
          { key: 'beneficial_owner', label: 'Beneficial owner', type: 'checkbox', fullWidth: true, checkboxLabel: 'Mark as beneficial owner' },
          { key: 'notes', label: 'Notes', type: 'textarea', fullWidth: true, placeholder: 'Compliance and transfer notes' },
        ]}
        formState={form}
        onFieldChange={handleChange}
        onSubmit={handleSubmit}
        onCancel={resetForm}
        onEdit={handleEdit}
        onDelete={handleDelete}
        editingLabel={editingId ? 'Edit shareholder' : ''}
        saving={saving}
        loading={loading}
        error={error}
      />

      <section className="eq-screen">
        <div className="eq-crud-layout">
          <aside className="eq-data-card eq-form-card">
            <div className="eq-data-card-head">
              <h3>{editingHoldingId ? 'Edit Holding Terms' : 'Add Holding Terms'}</h3>
              {editingHoldingId && <button type="button" className="eq-inline-btn secondary" onClick={resetHoldingForm}>Cancel edit</button>}
            </div>
            <p className="eq-form-copy">Maintain investor cost basis and pro-rata elections directly on each holding so dilution and waterfall outputs reflect actual economics.</p>
            <form className="eq-form-grid" onSubmit={handleHoldingSubmit}>
              <label className="eq-form-field">
                <span className="eq-form-label">Shareholder</span>
                <select className="eq-form-select" value={holdingForm.shareholder} onChange={(event) => setHoldingForm((current) => ({ ...current, shareholder: event.target.value }))}>
                  <option value="">Select shareholder</option>
                  {shareholders.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Share class</span>
                <select className="eq-form-select" value={holdingForm.share_class} onChange={(event) => setHoldingForm((current) => ({ ...current, share_class: event.target.value }))}>
                  <option value="">Select share class</option>
                  {shareClasses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Issued shares</span>
                <input className="eq-form-input" type="number" min="0" step="1" value={holdingForm.quantity} onChange={(event) => setHoldingForm((current) => ({ ...current, quantity: event.target.value }))} />
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Fully diluted shares</span>
                <input className="eq-form-input" type="number" min="0" step="1" value={holdingForm.diluted_quantity} onChange={(event) => setHoldingForm((current) => ({ ...current, diluted_quantity: event.target.value }))} />
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Issue price / share</span>
                <input className="eq-form-input" type="number" min="0" step="0.0001" value={holdingForm.issue_price_per_share} onChange={(event) => setHoldingForm((current) => ({ ...current, issue_price_per_share: event.target.value }))} />
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Invested amount</span>
                <input className="eq-form-input" type="number" min="0" step="0.01" value={holdingForm.invested_amount} onChange={(event) => setHoldingForm((current) => ({ ...current, invested_amount: event.target.value }))} />
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Issued date</span>
                <input className="eq-form-input" type="date" value={holdingForm.issued_at} onChange={(event) => setHoldingForm((current) => ({ ...current, issued_at: event.target.value }))} />
              </label>
              <label className="eq-form-field">
                <span className="eq-form-label">Pro-rata take-up %</span>
                <input className="eq-form-input" type="number" min="0" step="0.01" value={holdingForm.pro_rata_take_up_percent} onChange={(event) => setHoldingForm((current) => ({ ...current, pro_rata_take_up_percent: event.target.value }))} />
              </label>
              <label className="eq-form-checkbox full">
                <input type="checkbox" checked={holdingForm.pro_rata_eligible} onChange={(event) => setHoldingForm((current) => ({ ...current, pro_rata_eligible: event.target.checked }))} />
                <span>Holder is eligible for pro-rata participation</span>
              </label>
              <div className="eq-form-actions">
                <button type="submit" className="eq-inline-btn primary" disabled={saving}>{saving ? 'Saving…' : editingHoldingId ? 'Save holding' : 'Create holding'}</button>
              </div>
            </form>
          </aside>

          <div className="eq-data-card">
            <div className="eq-data-card-head">
              <h3>Holding Economics</h3>
              {loading && <span className="eq-status-chip">Syncing</span>}
            </div>
            <div className="eq-table-wrap">
              <table className="eq-table">
                <thead>
                  <tr>
                    <th>Holder</th>
                    <th>Class</th>
                    <th>Issued</th>
                    <th>FD Shares</th>
                    <th>Issue Price</th>
                    <th>Invested</th>
                    <th>Pro-Rata</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((record) => (
                    <tr key={record.id}>
                      <td>{record.shareholder_name}</td>
                      <td>{record.share_class_name}</td>
                      <td>{record.quantity}</td>
                      <td>{record.diluted_quantity}</td>
                      <td>{record.issue_price_per_share}</td>
                      <td>{record.invested_amount}</td>
                      <td>{record.pro_rata_eligible ? `${record.pro_rata_take_up_percent}%` : 'No'}</td>
                      <td>
                        <div className="eq-table-actions">
                          <button type="button" className="eq-inline-btn" onClick={() => handleHoldingEdit(record)}>Edit</button>
                          <button type="button" className="eq-inline-btn danger" onClick={() => handleHoldingDelete(record)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default OwnershipRegistry;
