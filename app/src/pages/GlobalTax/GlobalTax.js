import React, { useEffect, useState } from 'react';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import { taxAPI } from '../../services/api';
import localCountries from '../../data/tax/countries.json';
import { normalizeTaxDirectory } from '../../utils/taxDirectory';
import './GlobalTax.css';

const fallbackCountries = normalizeTaxDirectory(localCountries);

const GlobalTax = () => {
  const [countries, setCountries] = useState(fallbackCountries);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(fallbackCountries[0] || null);
  const [regionFilter, setRegionFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [isUsingFallback, setIsUsingFallback] = useState(false);

  useEffect(() => {
    setLoading(true);
    taxAPI.list()
      .then((res) => {
        const liveCountries = normalizeTaxDirectory(res.data);
        const nextCountries = liveCountries.length > 0 ? liveCountries : fallbackCountries;
        setCountries(nextCountries);
        setSelected((currentSelected) => {
          if (!currentSelected) {
            return nextCountries[0] || null;
          }

          return nextCountries.find((country) => country.code === currentSelected.code) || nextCountries[0] || null;
        });
        setIsUsingFallback(liveCountries.length === 0);
      })
      .catch(() => {
        setCountries(fallbackCountries);
        setSelected((currentSelected) => currentSelected || fallbackCountries[0] || null);
        setIsUsingFallback(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const regions = ['Africa', 'Americas', 'Asia', 'Europe', 'Oceania', 'Territories'].filter(
    r => countries.some(c => c.region === r)
  );

  const filtered = countries
    .filter(c => (regionFilter ? c.region === regionFilter : true))
    .filter(c => c.name.toLowerCase().includes(query.toLowerCase()) || c.code.toLowerCase().includes(query.toLowerCase()));

  const totalRegions = new Set(countries.map((country) => country.region).filter(Boolean)).size;
  const selectedCountry = selected && filtered.some((country) => country.code === selected.code)
    ? selected
    : filtered[0] || selected;
  const quickActionCount = [
    Boolean(selectedCountry?.supported_tasks?.includes('open_tax_payment_portal') && selectedCountry?.tax_authority?.payment_portal),
    Boolean(selectedCountry?.supported_tasks?.includes('basic_tax_estimator')),
  ].filter(Boolean).length;

  return (
    <div className="global-tax-page">
      <Header />

      <main>
        {/* Hero Section */}
        <div className="tax-hero">
          <div className="tax-hero-content">
            <h1 className="tax-hero-title">Global Tax Directory</h1>
            <p className="tax-hero-subtitle">Comprehensive tax guidance for 200+ jurisdictions worldwide</p>
            <p className="tax-hero-description">Access verified tax authority information, payment portals, and expert summaries from PwC, Deloitte, and EY.
              No login required.
            </p>
            <div className="tax-overview-grid">
              <div className="tax-overview-card">
                <span className="overview-label">Jurisdictions</span>
                <strong>{countries.length}</strong>
              </div>
              <div className="tax-overview-card">
                <span className="overview-label">Regions</span>
                <strong>{totalRegions}</strong>
              </div>
              <div className="tax-overview-card">
                <span className="overview-label">Sources</span>
                <strong>PwC, Deloitte, EY</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Search & Filter Section */}
        <div className="tax-search-section">
          <div className="tax-search-container">
            <div className="search-input-wrapper">

              <input
                className="tax-search-input"
                placeholder="Search by country name or code (e.g., United States, US)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <select value={regionFilter} onChange={e => setRegionFilter(e.target.value)} className="tax-region-select">
              <option value="">All Regions</option>
              {regions.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            <span className="results-count">{filtered.length} jurisdictions</span>
          </div>
          {isUsingFallback && (
            <div className="tax-status-banner">
              Showing the bundled jurisdiction directory while the live tax endpoint is unavailable.
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="tax-content-wrapper">
          {loading && countries.length === 0 ? (
            <div className="tax-loading">
              <div className="spinner"></div>
              <p>Loading tax data...</p>
            </div>
          ) : (
            <div className="tax-grid">
              {/* Countries List */}
              <div className="tax-list-wrapper">
                <div className="tax-list-header">
                  <h3>Jurisdictions</h3>
                  <span className="list-count">{filtered.length}</span>
                </div>
                <div className="tax-list">
                  {filtered.map(c => (
                    <button
                      key={c.code}
                      type="button"
                      className={`tax-list-item ${selectedCountry?.code === c.code ? 'active' : ''}`}
                      onClick={() => setSelected(c)}
                      aria-pressed={selectedCountry?.code === c.code}
                      aria-label={`View tax information for ${c.name}`}
                    >
                      <div className="item-content">
                        <div className="country-name">{c.name}</div>
                        <div className="country-region">{c.region}</div>
                      </div>
                      <div className="country-code">{c.code}</div>
                    </button>
                  ))}
                  {filtered.length === 0 && (
                    <div className="empty-list">No jurisdictions match your search</div>
                  )}
                </div>
              </div>

              {/* Details Panel */}
              <div className="tax-details-wrapper">
                {!selectedCountry ? (
                  <div className="empty-panel">
                    <div className="empty-icon"></div>
                    <h3>Select a Jurisdiction</h3>
                    <p>Choose a country from the list to view comprehensive tax information</p>
                  </div>
                ) : (
                  <div className="country-details">
                    {/* Header */}
                    <div className="details-header">
                      <div className="header-title">
                        <h2>{selectedCountry.name}</h2>
                        <span className="country-code-badge">{selectedCountry.code}</span>
                      </div>
                      <span className="region-badge">{selectedCountry.region}</span>
                    </div>

                    {/* Tax Authority */}
                    <div className="section-card authority-card">
                      <h4 className="section-title">Tax Authority</h4>
                      <div className="authority-info">
                        <div className="info-row">
                          <span className="label">Official Name:</span>
                          <span className="value">{selectedCountry.tax_authority?.name || '—'}</span>
                        </div>
                        {selectedCountry.tax_authority?.website && (
                          <a href={selectedCountry.tax_authority.website} rel="noreferrer" className="primary-link">Visit Tax Authority Website →
                          </a>
                        )}
                        {selectedCountry.tax_authority?.payment_portal && (
                          <a href={selectedCountry.tax_authority.payment_portal} rel="noreferrer" className="secondary-link">Payment Portal →
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Tax Summaries */}
                    <div className="section-card summaries-card">
                      <h4 className="section-title">Tax Summaries</h4>
                      <div className="summaries-grid">
                        {selectedCountry.links?.corporate_tax_summary && (
                          <a href={selectedCountry.links.corporate_tax_summary} rel="noreferrer" className="summary-link">
                            <span className="icon"></span>
                            <span>Corporate Tax</span>
                          </a>
                        )}
                        {selectedCountry.links?.personal_income_tax_summary && (
                          <a href={selectedCountry.links.personal_income_tax_summary} rel="noreferrer" className="summary-link">
                            <span className="icon"></span>
                            <span>Personal Tax</span>
                          </a>
                        )}
                        {selectedCountry.links?.vat_or_indirect_tax_summary && (
                          <a href={selectedCountry.links.vat_or_indirect_tax_summary} rel="noreferrer" className="summary-link">
                            <span className="icon"></span>
                            <span>VAT / GST</span>
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Global References */}
                    <div className="section-card references-card">
                      <h4 className="section-title">Expert References</h4>
                      <div className="references-list">
                        {selectedCountry.links?.global_references?.map((r, i) => (
                          <a key={i} href={r.url} rel="noreferrer" className="reference-link">
                            <span className="ref-icon"></span>
                            <span>{r.label}</span>
                          </a>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    {selectedCountry.supported_tasks && selectedCountry.supported_tasks.length > 0 && (
                      <div className="section-card actions-card">
                        <h4 className="section-title">Quick Actions</h4>
                        {selectedCountry.supported_tasks?.includes('open_tax_payment_portal') && selectedCountry.tax_authority?.payment_portal && (
                          <div className="actions-banner">Pay Tax Online</div>
                        )}
                        <div className={`actions-grid${quickActionCount === 1 ? ' actions-grid--single' : ''}`}>
                          {selectedCountry.supported_tasks?.includes('open_tax_payment_portal') && selectedCountry.tax_authority?.payment_portal && (
                            <a
                              href={selectedCountry.tax_authority.payment_portal}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="action-btn primary-btn"
                            >
                              <span className="action-btn__title">Pay Tax Online</span>
                            </a>
                          )}
                          {selectedCountry.supported_tasks?.includes('basic_tax_estimator') && (
                            <button
                              className="action-btn secondary-btn"
                              type="button"
                            >
                              <span className="action-btn__title">Estimate Tax</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default GlobalTax;
