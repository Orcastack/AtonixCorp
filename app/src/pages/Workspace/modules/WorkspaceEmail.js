import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { useEnterprise } from '../../../context/EnterpriseContext';
import { organizationsAPI } from '../../../services/api';
import './WorkspaceModules.css';

const formatDateTime = (value) => value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Not sent';

const WorkspaceEmail = () => {
  const { user } = useAuth();
  const { currentOrganization } = useEnterprise();
  const [composing, setComposing] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [emailData, setEmailData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [accountForm, setAccountForm] = useState({ local_part: '', display_name: '' });
  const [campaignForm, setCampaignForm] = useState({ sender_id: '', campaign_type: 'operational', recipients: '', subject: '', html_body: '', consent_confirmed: false });
  const isOwner = Boolean(currentOrganization?.owner_email && currentOrganization.owner_email === user?.email);

  const loadEmailService = useCallback(async () => {
    if (!currentOrganization?.id || !isOwner) {
      setEmailData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await organizationsAPI.getEmailService(currentOrganization.id);
      setEmailData(response.data);
      setCampaignForm((current) => ({ ...current, sender_id: current.sender_id || response.data.accounts?.[0]?.id || '' }));
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to load organization email service.');
    } finally {
      setLoading(false);
    }
  }, [currentOrganization?.id, isOwner]);

  useEffect(() => {
    loadEmailService();
  }, [loadEmailService]);

  const configureTier = async (tier) => {
    setBusy(true);
    setMessage('');
    try {
      await organizationsAPI.configureEmailSubscription(currentOrganization.id, { tier });
      await loadEmailService();
      setMessage(`Email service is now configured for the ${tier} tier.`);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Unable to configure email service tier.');
    } finally {
      setBusy(false);
    }
  };

  const provisionAccount = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      await organizationsAPI.provisionEmailAccount(currentOrganization.id, accountForm);
      setAccountForm({ local_part: '', display_name: '' });
      setProvisioning(false);
      await loadEmailService();
      setMessage('Workspace sender identity provisioned.');
    } catch (error) {
      setMessage(error.response?.data?.detail || error.response?.data?.subscription || 'Unable to provision sender identity.');
    } finally {
      setBusy(false);
    }
  };

  const sendCampaign = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const recipients = campaignForm.recipients.split(/[\n,;]/).map((recipient) => recipient.trim()).filter(Boolean);
      const response = await organizationsAPI.sendEmailCampaign(currentOrganization.id, { ...campaignForm, recipients });
      setComposing(false);
      setCampaignForm((current) => ({ ...current, recipients: '', subject: '', html_body: '', consent_confirmed: false }));
      await loadEmailService();
      setMessage(`Delivery completed: ${response.data.sent_count} sent, ${response.data.failed_count} failed.`);
    } catch (error) {
      const details = error.response?.data;
      setMessage(details?.detail || details?.recipients || details?.subscription || details?.consent_confirmed || 'Unable to send email.');
    } finally {
      setBusy(false);
    }
  };

  if (!isOwner) {
    return (
      <div className="wsm-page">
        <div className="wsm-page-header"><div><h1 className="wsm-page-title">Organization Email</h1><p className="wsm-page-sub">Managed outbound email is administered by the organization owner.</p></div></div>
        <div className="wsm-empty">Your current role cannot view recipients, delivery records, or sender identities.</div>
      </div>
    );
  }

  const subscription = emailData?.subscription;

  return (
    <div className="wsm-page">
      <div className="wsm-page-header">
        <div>
          <h1 className="wsm-page-title">Organization Email</h1>
          <p className="wsm-page-sub">Audited outbound email for governance, operational notices, and consent-based campaigns.</p>
        </div>
        <button className="wsm-btn-primary" onClick={() => setComposing(true)} disabled={!emailData?.accounts?.length || busy}>+ Compose</button>
      </div>

      {message && <div className="wsm-permission-note">{message}</div>}
      {loading ? <div className="wsm-empty">Loading organization email service...</div> : (
        <>
          <div className="wsm-stats-row">
            <div className="wsm-stat-card"><span className="wsm-stat-label">Service Tier</span><span className="wsm-stat-value">{subscription?.tier || 'basic'}</span></div>
            <div className="wsm-stat-card"><span className="wsm-stat-label">Sender Identities</span><span className="wsm-stat-value">{emailData?.accounts?.length || 0}{subscription?.account_limit !== null ? ` / ${subscription?.account_limit}` : ''}</span></div>
            <div className="wsm-stat-card"><span className="wsm-stat-label">Monthly Volume</span><span className="wsm-stat-value">{subscription?.sent_this_month || 0} / {subscription?.monthly_send_limit || 0}</span></div>
            <div className="wsm-stat-card"><span className="wsm-stat-label">Marketing Tools</span><span className="wsm-stat-value">{subscription?.marketing_enabled ? 'Enabled' : 'Enterprise'}</span></div>
          </div>

          <div className="wsm-toolbar">
            <div className="wsm-chips">{['basic', 'professional', 'enterprise'].map((tier) => <button key={tier} className={`wsm-chip${subscription?.tier === tier ? ' active' : ''}`} onClick={() => configureTier(tier)} disabled={busy}>{tier}</button>)}</div>
            <button className="wsm-btn-secondary" onClick={() => setProvisioning(true)} disabled={busy}>Provision sender</button>
          </div>

          <div className="wsm-table-wrap"><table className="wsm-table"><thead><tr><th>Recipient</th><th>Subject</th><th>Type</th><th>Status</th><th>Sent</th></tr></thead><tbody>{emailData?.deliveries?.length ? emailData.deliveries.map((delivery) => <tr key={delivery.id}><td>{delivery.recipient}</td><td>{delivery.subject}</td><td>{delivery.event_type}</td><td>{delivery.status}</td><td>{formatDateTime(delivery.sent_at || delivery.created_at)}</td></tr>) : <tr><td colSpan={5}><div className="wsm-empty">No email deliveries have been recorded.</div></td></tr>}</tbody></table></div>
        </>
      )}

      {provisioning && (
        <div className="wsm-modal-overlay"><form className="wsm-modal-card" onSubmit={provisionAccount}><h3 className="wsm-modal-title">Provision Sender Identity</h3><div className="wsm-form"><div className="wsm-form-group"><label className="wsm-label">Sender name</label><input className="wsm-input" value={accountForm.local_part} onChange={(event) => setAccountForm({ ...accountForm, local_part: event.target.value })} placeholder="governance" required /></div><div className="wsm-form-group"><label className="wsm-label">Display name</label><input className="wsm-input" value={accountForm.display_name} onChange={(event) => setAccountForm({ ...accountForm, display_name: event.target.value })} placeholder={currentOrganization?.name} /></div><div className="wsm-modal-actions"><button type="button" className="wsm-btn-secondary" onClick={() => setProvisioning(false)}>Cancel</button><button className="wsm-btn-primary" disabled={busy}>{busy ? 'Provisioning...' : 'Provision sender'}</button></div></div></form></div>
      )}

      {composing && (
        <div className="wsm-modal-overlay">
          <form className="wsm-modal-card wsm-modal-card-wide" onSubmit={sendCampaign}>
            <h3 className="wsm-modal-title">New Organization Message</h3>
            <div className="wsm-form">
              <div className="wsm-form-group"><label className="wsm-label">From</label><select className="wsm-input" value={campaignForm.sender_id} onChange={(event) => setCampaignForm({ ...campaignForm, sender_id: event.target.value })}>{emailData?.accounts?.map((account) => <option key={account.id} value={account.id}>{account.display_name || account.address} &lt;{account.address}&gt;</option>)}</select></div>
              <div className="wsm-form-group"><label className="wsm-label">Message type</label><select className="wsm-input" value={campaignForm.campaign_type} onChange={(event) => setCampaignForm({ ...campaignForm, campaign_type: event.target.value })}><option value="governance">Governance notice</option><option value="operational">Operational notice</option><option value="marketing" disabled={!subscription?.marketing_enabled}>Marketing campaign</option></select></div>
              <div className="wsm-form-group"><label className="wsm-label">Recipients</label><textarea className="wsm-textarea" rows={3} value={campaignForm.recipients} onChange={(event) => setCampaignForm({ ...campaignForm, recipients: event.target.value })} placeholder="recipient@example.com, another@example.com" required /></div>
              <div className="wsm-form-group"><label className="wsm-label">Subject</label><input className="wsm-input" value={campaignForm.subject} onChange={(event) => setCampaignForm({ ...campaignForm, subject: event.target.value })} required /></div>
              <div className="wsm-form-group"><label className="wsm-label">Message</label><textarea className="wsm-textarea" rows={6} value={campaignForm.html_body} onChange={(event) => setCampaignForm({ ...campaignForm, html_body: event.target.value })} required /></div>
              {campaignForm.campaign_type === 'marketing' && <label className="wsm-permission-note"><input type="checkbox" checked={campaignForm.consent_confirmed} onChange={(event) => setCampaignForm({ ...campaignForm, consent_confirmed: event.target.checked })} /> I confirm every recipient has provided marketing consent and the message includes a lawful purpose.</label>}
              <div className="wsm-modal-actions"><button type="button" className="wsm-btn-secondary" onClick={() => setComposing(false)}>Cancel</button><button className="wsm-btn-primary" disabled={busy}>{busy ? 'Sending...' : 'Send audited email'}</button></div>
            </div>
          </form>
        </div>
      )}
      <div className="wsm-permission-note"><strong>Compliance:</strong> Sender identities, campaigns, and delivery events are audited. Marketing requires Enterprise tier and recorded recipient consent. DNS authentication and inbound mailbox hosting are configured with the SMTP/mail provider.</div>
    </div>
  );
};

export default WorkspaceEmail;
