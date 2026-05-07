import React, { useState, useEffect } from 'react';
import { useEnterprise } from '../../context/EnterpriseContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const CATEGORIES = ['All', 'Integration', 'Add-on', 'Partner Service'];

const CATALOG = [
  // Banking & Payments
  {
    id: 'stripe', name: 'Stripe Payments', category: 'Integration',
    provider: 'Stripe Inc.', color: 'var(--color-cyan-dark)',
    description: 'Accept payments, manage subscriptions, and process refunds directly within the platform.',
    tags: ['payments', 'billing', 'subscriptions'],
    rating: 4.9, reviews: 1240, featured: true,
    features: ['Accept 135+ currencies', 'Automated invoice payments', 'Real-time reconciliation'],
  },
  {
    id: 'plaid', name: 'Plaid Bank Connect', category: 'Integration',
    provider: 'Plaid Technologies', color: 'var(--color-cyan-dark)',
    description: 'Connect and sync transactions from 11,000+ financial institutions automatically.',
    tags: ['banking', 'transactions', 'reconciliation'],
    rating: 4.8, reviews: 875, featured: true,
    features: ['11,000+ banks', 'Real-time transaction sync', 'Balance tracking'],
  },
  {
    id: 'paypal', name: 'PayPal Business', category: 'Integration',
    provider: 'PayPal Holdings', color: 'var(--color-cyan-dark)',
    description: 'Collect payments and manage PayPal transactions alongside your bookkeeping.',
    tags: ['payments', 'invoicing'],
    rating: 4.5, reviews: 640, featured: false,
    features: ['Invoice payments', 'Multi-currency', 'Dispute management'],
  },
  // Tax & Compliance
  {
    id: 'avalara', name: 'Avalara Tax Automation', category: 'Integration',
    provider: 'Avalara Inc.', color: 'var(--color-warning)',
    description: 'Real-time tax rates and automated compliance for 12,000+ tax jurisdictions worldwide.',
    tags: ['tax', 'compliance', 'automation'],
    rating: 4.7, reviews: 520, featured: true,
    features: ['12,000+ jurisdictions', 'Automated filings', 'Compliance monitoring'],
  },
  {
    id: 'taxjar', name: 'TaxJar', category: 'Integration',
    provider: 'TaxJar by Stripe', color: 'var(--color-cyan)',
    description: 'Sales tax calculations, nexus tracking, and automated returns for eCommerce and SaaS.',
    tags: ['tax', 'sales-tax', 'ecommerce'],
    rating: 4.6, reviews: 380, featured: false,
    features: ['Nexus tracking', 'AutoFile returns', 'Economic nexus alerts'],
  },
  // Payroll
  {
    id: 'gusto', name: 'Gusto Payroll', category: 'Integration',
    provider: 'Gusto Inc.', color: 'var(--color-error)',
    description: 'Full-service payroll processing with automatic tax filings and benefits management.',
    tags: ['payroll', 'hr', 'benefits'],
    rating: 4.8, reviews: 920, featured: true,
    features: ['Automated payroll', 'Benefits management', 'W-2/1099 filing'],
  },
  {
    id: 'adp', name: 'ADP Run', category: 'Integration',
    provider: 'ADP LLC', color: 'var(--color-error)',
    description: 'Enterprise payroll processing, HR administration, and workforce management.',
    tags: ['payroll', 'enterprise', 'hr'],
    rating: 4.5, reviews: 750, featured: false,
    features: ['Enterprise-grade payroll', 'Time tracking', 'Compliance reporting'],
  },
  // Add-ons
  {
    id: 'ai_advisor', name: 'AI Financial Advisor', category: 'Add-on',
    provider: 'Ledgora AI', color: 'var(--color-cyan-dark)',
    description: 'AI-powered financial insights, anomaly detection, and predictive cash flow forecasting.',
    tags: ['ai', 'analytics', 'forecasting'],
    rating: 4.9, reviews: 445, featured: true,
    features: ['Anomaly detection', 'Cash flow forecasting', 'Smart recommendations'],
  },
  {
    id: 'doc_automation', name: 'Document Automation', category: 'Add-on',
    provider: 'Ledgora Labs', color: 'var(--color-cyan)',
    description: 'Auto-generate financial reports, proposals, and engagement letters from templates.',
    tags: ['documents', 'automation', 'reports'],
    rating: 4.7, reviews: 310, featured: false,
    features: ['Template engine', 'e-Signature', 'Automated sending'],
  },
  {
    id: 'client_portal', name: 'Enhanced Client Portal', category: 'Add-on',
    provider: 'Ledgora Labs', color: 'var(--color-success)',
    description: 'Branded self-service portal for clients with real-time financial visibility.',
    tags: ['portal', 'clients', 'collaboration'],
    rating: 4.8, reviews: 280, featured: false,
    features: ['Custom branding', 'Document sharing', 'Live messaging'],
  },
  {
    id: 'security_vault', name: 'Security Vault Pro', category: 'Add-on',
    provider: 'Ledgora Security', color: 'var(--color-error)',
    description: 'Advanced encryption, multi-factor authentication, and audit trail capabilities.',
    tags: ['security', 'compliance', 'encryption'],
    rating: 4.9, reviews: 195, featured: false,
    features: ['256-bit AES encryption', 'MFA enforcement', 'Immutable audit logs'],
  },
  {
    id: 'notifications_pro', name: 'Smart Alerts Pro', category: 'Add-on',
    provider: 'Ledgora Labs', color: 'var(--color-warning)',
    description: 'Multi-channel alerts (email, SMS, WhatsApp) with custom threshold triggers.',
    tags: ['notifications', 'alerts', 'sms'],
    rating: 4.6, reviews: 220, featured: false,
    features: ['SMS & WhatsApp alerts', 'Custom thresholds', 'Escalation workflows'],
  },
  // Partner Services
  {
    id: 'kpmg_advisory', name: 'KPMG Advisory Connect', category: 'Partner Service',
    provider: 'KPMG International', color: 'var(--color-cyan-dark)',
    description: 'Direct access to KPMG advisory services for tax planning, audits, and M&A support.',
    tags: ['advisory', 'audit', 'tax-planning'],
    rating: 4.9, reviews: 130, featured: true,
    features: ['On-demand advisory', 'Audit support', 'M&A due diligence'],
  },
  {
    id: 'r2r', name: 'R2R Cloud Accounting', category: 'Partner Service',
    provider: 'R2R Partners Group', color: 'var(--color-cyan-dark)',
    description: 'Outsourced CFO and controller services from certified accounting professionals.',
    tags: ['outsourcing', 'cfo', 'controller'],
    rating: 4.7, reviews: 88, featured: false,
    features: ['Virtual CFO', 'Controller services', 'Monthly close support'],
  },
  {
    id: 'inventory_link', name: 'InventoryLink', category: 'Partner Service',
    provider: 'SupplyChain.io', color: 'var(--color-success)',
    description: 'Connect your inventory management system for automated COGS and stock tracking.',
    tags: ['inventory', 'cogs', 'supply-chain'],
    rating: 4.5, reviews: 160, featured: false,
    features: ['Automated COGS', 'Multi-warehouse', 'Low-stock alerts'],
  },
];

const Marketplace = () => {
  const { currentOrganization } = useEnterprise();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [installed, setInstalled] = useState({});
  const [installing, setInstalling] = useState({});
  const [selectedItem, setSelectedItem] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!currentOrganization) return;
    const token = localStorage.getItem('access_token');
    fetch(`${API_BASE}/client-marketplace-integrations/?organization=${currentOrganization.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        const items = Array.isArray(data) ? data : data.results || [];
        const installedMap = {};
        items.forEach(i => { installedMap[i.provider?.toLowerCase().replace(/\s/g, '_')] = true; });
        setInstalled(installedMap);
      })
      .catch(() => {});
  }, [currentOrganization]);

  const handleInstall = async (item) => {
    setInstalling(prev => ({ ...prev, [item.id]: true }));
    const token = localStorage.getItem('access_token');
    try {
      await fetch(`${API_BASE}/client-marketplace-integrations/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization: currentOrganization?.id,
          client: null,
          name: item.name,
          category: item.category.toLowerCase().replace(/\s/g, '_'),
          provider: item.provider,
          description: item.description,
          is_active: true,
        }),
      });
    } catch (e) {
      // Demo mode fallback
    }
    setTimeout(() => {
      setInstalled(prev => ({ ...prev, [item.id]: true }));
      setInstalling(prev => ({ ...prev, [item.id]: false }));
    }, 1200);
  };

  const handleUninstall = (item) => {
    setInstalled(prev => { const n = { ...prev }; delete n[item.id]; return n; });
  };

  const filtered = CATALOG.filter(item => {
    const matchesCategory = category === 'All' || item.category === category;
    const q = search.toLowerCase();
    const matchesSearch = !q ||
      item.name.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.tags.some(t => t.includes(q));
    return matchesCategory && matchesSearch;
  });

  const featured = filtered.filter(i => i.featured);
  const regular = filtered.filter(i => !i.featured);

  const openDetail = (item) => { setSelectedItem(item); setShowModal(true); };

  return (
    <div className="marketplace">
      {/* Header */}
      <div className="mp-header">
        <div>
          <h1>Marketplace</h1>
          <p>Extend your platform with integrations, add-ons, and partner services</p>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="mp-toolbar">
        <div className="mp-search">

          <input
            type="text"
            placeholder="Search integrations, add-ons, partners…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="mp-category-tabs">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              className={`cat-tab ${category === cat ? 'active' : ''}`}
              onClick={() => setCategory(cat)}
            >

              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Installed count */}
      {Object.keys(installed).length > 0 && (
        <div className="mp-installed-bar">
           <strong>{Object.keys(installed).length}</strong> integration(s) active
        </div>
      )}

      {/* Featured */}
      {featured.length > 0 && (
        <div className="mp-section">
          <h2 className="mp-section-title">Featured</h2>
          <div className="mp-featured-grid">
            {featured.map(item => (
              <div className="mp-featured-card" key={item.id} onClick={() => openDetail(item)}>
                <div className="mfc-icon" style={{ background: item.color + '18', color: item.color }}>
                  {item.icon}
                </div>
                <div className="mfc-body">
                  <div className="mfc-name">{item.name}</div>
                  <div className="mfc-provider">{item.provider}</div>
                  <div className="mfc-desc">{item.description}</div>
                  <div className="mfc-tags">
                    {item.tags.slice(0, 3).map(t => <span className="tag" key={t}>{t}</span>)}
                  </div>
                  <div className="mfc-footer">
                    <span className="rating"> {item.rating} ({item.reviews})</span>
                    {installed[item.id] ? (
                      <button className="btn-installed" onClick={e => { e.stopPropagation(); handleUninstall(item); }}>
                        Installed
                      </button>
                    ) : (
                      <button className="btn-install" onClick={e => { e.stopPropagation(); handleInstall(item); }}>
                        {installing[item.id] ? 'Installing…' : <>Install</>}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Regular items */}
      {regular.length > 0 && (
        <div className="mp-section">
          <h2 className="mp-section-title">
            {category === 'All' ? 'All Integrations & Add-ons' : category}
          </h2>
          <div className="mp-grid">
            {regular.map(item => (
              <div className="mp-card" key={item.id} onClick={() => openDetail(item)}>
                <div className="mpc-top">
                  <div className="mpc-icon" style={{ background: item.color + '18', color: item.color }}>
                    {item.icon}
                  </div>
                  <div className="mpc-meta">
                    <div className="mpc-name">{item.name}</div>
                    <div className="mpc-cat"><span className="cat-badge">{item.category}</span></div>
                  </div>
                </div>
                <div className="mpc-desc">{item.description}</div>
                <div className="mpc-footer">
                  <span className="rating"> {item.rating}</span>
                  {installed[item.id] ? (
                    <button className="btn-installed sm" onClick={e => { e.stopPropagation(); handleUninstall(item); }}>
                      Active
                    </button>
                  ) : (
                    <button className="btn-install sm" onClick={e => { e.stopPropagation(); handleInstall(item); }}>
                      {installing[item.id] ? '…' : 'Install'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="mp-empty">

          <h2>No results found</h2>
          <p>Try a different search term or category.</p>
        </div>
      )}

      {/* Detail Modal */}
      {showModal && selectedItem && (
        <div className="mp-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="mp-modal" onClick={e => e.stopPropagation()}>
            <button className="mp-modal-close" onClick={() => setShowModal(false)}></button>
            <div className="modal-header">
              <div className="modal-icon" style={{ background: selectedItem.color + '18', color: selectedItem.color }}>
                {selectedItem.icon}
              </div>
              <div>
                <h2>{selectedItem.name}</h2>
                <div className="modal-provider">{selectedItem.provider}</div>
                <span className="cat-badge">{selectedItem.category}</span>
              </div>
            </div>
            <p className="modal-desc">{selectedItem.description}</p>
            <div className="modal-features">
              <h3>Key Features</h3>
              <ul>
                {selectedItem.features.map((f, i) => (
                  <li key={i}> {f}</li>
                ))}
              </ul>
            </div>
            <div className="modal-tags">
              {selectedItem.tags.map(t => <span className="tag" key={t}>{t}</span>)}
            </div>
            <div className="modal-footer">
              <span className="modal-rating"> {selectedItem.rating} · {selectedItem.reviews} reviews</span>
              {installed[selectedItem.id] ? (
                <button className="btn-installed" onClick={() => handleUninstall(selectedItem)}>
                  Installed — Click to Remove
                </button>
              ) : (
                <button className="btn-install large" onClick={() => { handleInstall(selectedItem); setShowModal(false); }}>
                  {installing[selectedItem.id] ? 'Installing…' : <>Install Now</>}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Marketplace;
