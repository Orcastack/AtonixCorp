import React, { useState } from 'react';
import { useEnterprise } from '../../../context/EnterpriseContext';
import './WorkspaceModules.css';

const MODULES = [
  { key: 'overview',    name: 'Overview',   desc: 'Workspace activity summary, stats, and highlights.', required: true  },
  { key: 'members',     name: 'Members',    desc: 'Member directory and role management.',               required: true  },
  { key: 'groups',      name: 'Departments',desc: 'Organise members into finance departments and operating units.', required: true  },
  { key: 'meetings',    name: 'Meetings',   desc: 'Schedule and track workspace meetings.',             required: true  },
  { key: 'calendar',    name: 'Calendar',   desc: 'Shared event and milestone calendar.',               required: true  },
  { key: 'files',       name: 'Files',      desc: 'Upload, share, and manage documents.',               required: true  },
  { key: 'permissions', name: 'Permissions',desc: 'Role-based access control matrix.',                  required: true  },
  { key: 'email',       name: 'Email',      desc: 'Workspace-scoped email inbox and compose.',          required: false },
  { key: 'marketing',   name: 'Marketing',  desc: 'Campaign management and engagement tools.',          required: false },
];

const WorkspaceSettings = () => {
  const { activeWorkspace } = useEnterprise();
  const ws = activeWorkspace || {};

  const [name, setName] = useState(ws.name || '');
  const [description, setDescription] = useState(ws.description || '');
  const [enabledModules, setEnabledModules] = useState(
    Object.fromEntries(MODULES.map(m => [m.key, true]))
  );

  const toggleModule = (key) => {
    setEnabledModules(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="wsm-page">
      <div className="wsm-page-header">
        <div>
          <h1 className="wsm-page-title">Settings</h1>
          <p className="wsm-page-sub">Configure workspace details, modules, and lifecycle.</p>
        </div>
      </div>

      {/* ── General ── */}
      <div className="wsm-section wsm-section-narrow">
        <div className="wsm-section-title">General</div>
        <div className="wsm-form">
          <div className="wsm-form-group">
            <label className="wsm-label">Workspace Name</label>
            <input className="wsm-input" value={name} onChange={e => setName(e.target.value)} placeholder="Enter workspace name" />
          </div>
          <div className="wsm-form-group">
            <label className="wsm-label">Description</label>
            <textarea className="wsm-textarea" rows={3} value={description} onChange={e => setDescription(e.target.value)} placeholder="Brief description of this workspace…" />
          </div>
          <div className="wsm-form-group">
            <label className="wsm-label">Status</label>
            <select className="wsm-select" defaultValue="active">
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="restricted">Restricted</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div>
            <button className="wsm-btn-primary">Save Changes</button>
          </div>
        </div>
      </div>

      {/* ── Modules ── */}
      <div className="wsm-section wsm-section-narrow">
        <div className="wsm-section-title">Modules</div>
        <div className="wsm-module-list">
          {MODULES.map(m => (
            <div key={m.key} className="wsm-module-item">
              <div className="wsm-module-info">
                <div className="wsm-module-name">{m.name}{m.required && <span className="wsm-module-required">(required)</span>}</div>
                <div className="wsm-module-desc">{m.desc}</div>
              </div>
              <label className="wsm-module-toggle">
                <input
                  type="checkbox"
                  checked={m.required || enabledModules[m.key]}
                  disabled={m.required}
                  onChange={() => !m.required && toggleModule(m.key)}
                />
                <span className="wsm-toggle-slider" />
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* ── Danger zone ── */}
      <div className="wsm-danger-zone wsm-section-narrow">
        <div className="wsm-danger-zone-copy">
          <div className="wsm-danger-zone-title">Ledgora Console Danger Zone</div>
          <div className="wsm-danger-zone-desc">
            Archiving or deleting the workspace is permanent. Archived workspaces retain data but become read-only.
          </div>
        </div>
        <div className="wsm-inline-actions wsm-inline-actions-danger">
          <button className="wsm-btn-secondary">Archive Workspace</button>
          <button className="wsm-btn-danger">Delete Workspace</button>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceSettings;
