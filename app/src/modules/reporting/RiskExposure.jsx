import React, { useState, useCallback } from 'react';
import { PageHeader, Card, Button, Modal, Input } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';

const BLANK_REPORT = { dateFrom: '', dateTo: '', currency: 'USD', entity: 'all', reportType: 'all' };

/* ── Mock data ── */
const fxExposure = [
  { currency: 'EUR', position:  1_250_000, rate: 1.085, usdValue:  1_356_250, unrealisedPL:  +18_400, direction: 'Long' },
  { currency: 'GBP', position:    820_000, rate: 1.270, usdValue:  1_040_400, unrealisedPL:   -6_200, direction: 'Long' },
  { currency: 'JPY', position: 45_000_000, rate: 0.0067, usdValue:  301_500, unrealisedPL:   +2_100, direction: 'Short' },
  { currency: 'CHF', position:    390_000, rate: 1.130, usdValue:    440_700, unrealisedPL:   +4_800, direction: 'Long' },
  { currency: 'AED', position:  2_100_000, rate: 0.2722, usdValue:   571_620, unrealisedPL:       0, direction: 'Flat' },
];

const arAging = [
  { counterparty: 'Meridian Holdings Ltd',   current: 48_200, days30: 22_000, days60:  8_400, days90plus:     0, total:  78_600 },
  { counterparty: 'Vantage Capital Corp',     current:  6_000, days30:     0, days60: 14_200, days90plus: 31_500, total:  51_700 },
  { counterparty: 'Apex Investments LLC',     current: 29_100, days30:  5_300, days60:     0, days90plus:     0, total:  34_400 },
  { counterparty: 'Sterling Advisory Group',  current:  3_800, days30: 12_000, days60:  6_100, days90plus:  8_900, total:  30_800 },
  { counterparty: 'Orion Financial Services', current:      0, days30:      0, days60:      0, days90plus: 27_200, total:  27_200 },
];

const concentration = [
  { name: 'Meridian Holdings Ltd',   exposure: 1_356_250, pct: 28.4, tier: 'A' },
  { name: 'Vantage Capital Corp',    exposure:   921_000, pct: 19.3, tier: 'B' },
  { name: 'Apex Investments LLC',    exposure:   740_800, pct: 15.5, tier: 'A' },
  { name: 'Sterling Advisory Group', exposure:   532_000, pct: 11.1, tier: 'B' },
  { name: 'Orion Financial Services',exposure:   389_000, pct:  8.1, tier: 'C' },
];

const fmtN = (n) =>
  n === 0 ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

const toneClass = (n) => (n > 0 ? 'positive' : n < 0 ? 'negative' : '');

/* ── CSV export ── */
const exportCSV = (rows, columns, filename) => {
  const header = columns.map((c) => `"${c.label}"`).join(',') + '\n';
  const body = rows.map((r) => columns.map((c) => `"${r[c.key]}"`).join(',')).join('\n');
  const blob = new Blob([header + body], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

export default function RiskExposure() {
  const { filters } = useFilters();
  const [activeTab, setActiveTab] = useState('fx');
  const [showRunModal, setShowRunModal] = useState(false);
  const [runForm, setRunForm] = useState(BLANK_REPORT);
  const setF = f => e => setRunForm(p => ({ ...p, [f]: e.target.value }));

  const totalFXExposure = fxExposure.reduce((s, r) => s + r.usdValue, 0);
  const totalUnrealisedPL = fxExposure.reduce((s, r) => s + r.unrealisedPL, 0);
  const overdueTotal = arAging.reduce((s, r) => s + r.days60 + r.days90plus, 0);
  const arTotal = arAging.reduce((s, r) => s + r.total, 0);

  const handleExport = useCallback(() => {
    if (activeTab === 'fx') {
      exportCSV(
        fxExposure.map((r) => ({ ...r, usdValue: fmtN(r.usdValue), unrealisedPL: fmtN(r.unrealisedPL) })),
        [
          { key: 'currency',     label: 'Currency'        },
          { key: 'direction',    label: 'Direction'       },
          { key: 'usdValue',     label: 'USD Equivalent'  },
          { key: 'unrealisedPL', label: 'Unrealised P&L'  },
        ],
        'fx-exposure.csv',
      );
    } else if (activeTab === 'aging') {
      exportCSV(
        arAging.map((r) => ({
          counterparty: r.counterparty,
          current:      fmtN(r.current),
          days30:       fmtN(r.days30),
          days60:       fmtN(r.days60),
          days90plus:   fmtN(r.days90plus),
          total:        fmtN(r.total),
        })),
        [
          { key: 'counterparty', label: 'Counterparty'  },
          { key: 'current',      label: 'Current'       },
          { key: 'days30',       label: '1-30 Days'     },
          { key: 'days60',       label: '31-60 Days'    },
          { key: 'days90plus',   label: '>60 Days'      },
          { key: 'total',        label: 'Total'         },
        ],
        'ar-aging.csv',
      );
    } else if (activeTab === 'conc') {
      exportCSV(
        concentration.map((r) => ({
          name:     r.name,
          tier:     r.tier,
          exposure: fmtN(r.exposure),
          pct:      r.pct.toFixed(1) + '%',
        })),
        [
          { key: 'name',     label: 'Counterparty'    },
          { key: 'tier',     label: 'Tier'            },
          { key: 'exposure', label: 'Exposure (USD)'  },
          { key: 'pct',      label: 'Portfolio %'     },
        ],
        'concentration-risk.csv',
      );
    }
  }, [activeTab]);

  return (
    <div className="module-page">
      <PageHeader
        title="Risk & Exposure"
        subtitle={`FX exposure, counterparty risk, and receivables aging · ${filters.currency} · ${
          filters.entity === 'all' ? 'All Entities' : `Entity ${filters.entity}`
        }`}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="secondary" size="small" onClick={handleExport}>Export CSV</Button>
            <Button variant="primary" size="small" onClick={() => setShowRunModal(true)}>Run Report</Button>
          </div>
        }
      />

      {/* Summary KPI row */}
      <div className="stats-row" style={{ marginBottom: 24 }}>
        <Card className="stat-card">
          <div className="stat-label">Total FX Exposure (USD)</div>
          <div className="stat-value">{fmtN(totalFXExposure)}</div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">Net Unrealised P&L</div>
          <div className={`stat-value ${toneClass(totalUnrealisedPL)}`}>{fmtN(totalUnrealisedPL)}</div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">AR Overdue (&gt;60 Days)</div>
          <div className="stat-value" style={{ color: overdueTotal > 0 ? 'var(--color-error)' : 'var(--color-success)' }}>
            {fmtN(overdueTotal)}
          </div>
        </Card>
        <Card className="stat-card">
          <div className="stat-label">Total Open Receivables</div>
          <div className="stat-value">{fmtN(arTotal)}</div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="statement-tabs">
        {[
          { id: 'fx',   label: 'FX Exposure' },
          { id: 'aging', label: 'AR Aging' },
          { id: 'conc', label: 'Concentration Risk' },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            className={`stmt-tab${activeTab === t.id ? ' active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* FX Exposure table */}
      {activeTab === 'fx' && (
        <Card>
          <table className="risk-table">
            <thead>
              <tr>
                <th>Currency</th>
                <th>Direction</th>
                <th className="num">Position</th>
                <th className="num">FX Rate</th>
                <th className="num">USD Equiv.</th>
                <th className="num">Unrealised P&L</th>
              </tr>
            </thead>
            <tbody>
              {fxExposure.map((r) => (
                <tr key={r.currency}>
                  <td><strong>{r.currency}</strong></td>
                  <td>
                    <span className={`risk-dir-badge ${r.direction.toLowerCase()}`}>{r.direction}</span>
                  </td>
                  <td className="num">{r.position.toLocaleString()}</td>
                  <td className="num">{r.rate.toFixed(4)}</td>
                  <td className="num">{fmtN(r.usdValue)}</td>
                  <td className={`num ${toneClass(r.unrealisedPL)}`}>
                    {r.unrealisedPL === 0 ? '—' : (r.unrealisedPL > 0 ? '+' : '') + fmtN(r.unrealisedPL)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="risk-total-row">
                <td colSpan={4}><strong>Total</strong></td>
                <td className="num"><strong>{fmtN(totalFXExposure)}</strong></td>
                <td className={`num ${toneClass(totalUnrealisedPL)}`}>
                  <strong>{totalUnrealisedPL > 0 ? '+' : ''}{fmtN(totalUnrealisedPL)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
          <p className="risk-disclaimer">
            Rates are indicative as of {filters.dateTo}. Positions are unhedged unless noted.
          </p>
        </Card>
      )}

      {/* AR Aging table */}
      {activeTab === 'aging' && (
        <Card>
          <table className="risk-table">
            <thead>
              <tr>
                <th>Counterparty</th>
                <th className="num">Current</th>
                <th className="num">1–30 Days</th>
                <th className="num">31–60 Days</th>
                <th className="num">&gt;60 Days</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {arAging.map((r) => (
                <tr key={r.counterparty}>
                  <td>{r.counterparty}</td>
                  <td className="num">{r.current ? fmtN(r.current) : '—'}</td>
                  <td className="num">{r.days30 ? fmtN(r.days30) : '—'}</td>
                  <td className={`num ${r.days60 > 0 ? 'warn' : ''}`}>{r.days60 ? fmtN(r.days60) : '—'}</td>
                  <td className={`num ${r.days90plus > 0 ? 'negative' : ''}`}>{r.days90plus ? fmtN(r.days90plus) : '—'}</td>
                  <td className="num"><strong>{fmtN(r.total)}</strong></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="risk-total-row">
                <td><strong>Total</strong></td>
                <td className="num">{fmtN(arAging.reduce((s, r) => s + r.current, 0))}</td>
                <td className="num">{fmtN(arAging.reduce((s, r) => s + r.days30, 0))}</td>
                <td className="num">{fmtN(arAging.reduce((s, r) => s + r.days60, 0))}</td>
                <td className="num negative">{fmtN(arAging.reduce((s, r) => s + r.days90plus, 0))}</td>
                <td className="num">{fmtN(arTotal)}</td>
              </tr>
            </tfoot>
          </table>
        </Card>
      )}

      {/* Concentration risk */}
      {activeTab === 'conc' && (
        <Card>
          <table className="risk-table">
            <thead>
              <tr>
                <th>Counterparty</th>
                <th>Tier</th>
                <th className="num">Exposure (USD)</th>
                <th className="num">Portfolio %</th>
                <th>Bar</th>
              </tr>
            </thead>
            <tbody>
              {concentration.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>
                    <span className={`risk-tier-badge tier-${r.tier.toLowerCase()}`}>{r.tier}</span>
                  </td>
                  <td className="num">{fmtN(r.exposure)}</td>
                  <td className="num">{r.pct.toFixed(1)}%</td>
                  <td>
                    <div className="conc-bar-track">
                      <div
                        className={`conc-bar-fill ${r.tier.toLowerCase()}`}
                        style={{ width: `${r.pct}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="risk-disclaimer">
            Concentration above 25% of portfolio in a single counterparty is flagged for review per internal policy.
          </p>
        </Card>
      )}
      <Modal
        isOpen={showRunModal}
        onClose={() => { setShowRunModal(false); setRunForm(BLANK_REPORT); }}
        title="Run Risk & Exposure Report"
      >
        <div className="form-grid">
          <div>
            <label className="input-label">Report Type</label>
            <select className="filter-select" style={{ width: '100%', height: 40 }} value={runForm.reportType} onChange={setF('reportType')}>
              <option value="all">All (FX + AR Aging + Concentration)</option>
              <option value="fx">FX Exposure Only</option>
              <option value="aging">AR Aging Only</option>
              <option value="conc">Concentration Risk Only</option>
            </select>
          </div>
          <div>
            <label className="input-label">Entity</label>
            <select className="filter-select" style={{ width: '100%', height: 40 }} value={runForm.entity} onChange={setF('entity')}>
              <option value="all">All Entities</option>
              <option value="1">Ledgora US</option>
              <option value="2">Ledgora UK</option>
            </select>
          </div>
          <div>
            <label className="input-label">Date From</label>
            <Input type="date" value={runForm.dateFrom} onChange={setF('dateFrom')} />
          </div>
          <div>
            <label className="input-label">Date To</label>
            <Input type="date" value={runForm.dateTo} onChange={setF('dateTo')} />
          </div>
          <div>
            <label className="input-label">Base Currency</label>
            <select className="filter-select" style={{ width: '100%', height: 40 }} value={runForm.currency} onChange={setF('currency')}>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <Button variant="secondary" onClick={() => { setShowRunModal(false); setRunForm(BLANK_REPORT); }}>Cancel</Button>
          <Button variant="primary" onClick={() => { setShowRunModal(false); setRunForm(BLANK_REPORT); }}>Generate Report</Button>
        </div>
      </Modal>
    </div>
  );
}
