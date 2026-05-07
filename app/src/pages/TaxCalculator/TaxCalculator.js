import React, { useState, useEffect } from 'react';

import taxCalculatorService from '../../services/taxCalculatorService';

const TaxCalculator = () => {
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [amount, setAmount] = useState('');
  const [taxType, setTaxType] = useState('corporate');
  const [result, setResult] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [alternatives, setAlternatives] = useState([]);
  const [compareCountries, setCompareCountries] = useState([]);
  const [showComparison, setShowComparison] = useState(false);
  const [currencySymbol, setCurrencySymbol] = useState('$');
  const [currencyCode, setCurrencyCode] = useState('USD');

  useEffect(() => {
    // Load countries on mount
    const countryList = taxCalculatorService.getCountries();
    setCountries(countryList);
  }, []);

  // Update currency when country changes
  const handleCountryChange = (country) => {
    setSelectedCountry(country);
    if (country) {
      const taxInfo = taxCalculatorService.getTaxInfo(country);
      if (taxInfo) {
        setCurrencySymbol(taxInfo.currencySymbol || '$');
        setCurrencyCode(taxInfo.currency || 'USD');
      }
    }
  };

  const handleCalculate = () => {
    if (!selectedCountry || !amount || amount <= 0) {
      alert('Please select a country and enter a valid amount');
      return;
    }

    const calculation = taxCalculatorService.calculateTax(selectedCountry, parseFloat(amount), taxType);

    if (!calculation.success) {
      alert(calculation.error);
      return;
    }

    setResult(calculation);

    // Get AI-powered suggestions
    const optimizations = taxCalculatorService.getOptimizationSuggestions(selectedCountry, parseFloat(amount), taxType);
    setSuggestions(optimizations);

    // Get tax-friendly alternatives
    const taxFriendly = taxCalculatorService.getTaxFriendlyAlternatives(selectedCountry, taxType, 5);
    setAlternatives(taxFriendly);
  };

  const handleCompare = () => {
    if (compareCountries.length === 0) {
      alert('Please select countries to compare');
      return;
    }
    setShowComparison(true);
  };

  const addCompareCountry = (country) => {
    if (!compareCountries.includes(country) && compareCountries.length < 5) {
      setCompareCountries([...compareCountries, country]);
    }
  };

  const removeCompareCountry = (country) => {
    setCompareCountries(compareCountries.filter(c => c !== country));
  };

  const getComparisonData = () => {
    return taxCalculatorService.compareTaxRates(compareCountries, taxType);
  };

  const getSuggestionIcon = (type) => {
    switch (type) {
      case 'success': return ;
      case 'warning': return ;
      case 'info': return ;
      default: return ;
    }
  };

  return (
    <div className="tax-calculator-page">
      <div className="page-header">
        <h1 className="page-title">
          AI-Powered Tax Calculator
        </h1>
        <p className="page-subtitle">Calculate taxes across 60+ countries with intelligent optimization suggestions
        </p>
      </div>

      {/* Main Calculator */}
      <div className="calculator-card">
        <h2>Calculate Tax</h2>

        <div className="calculator-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="country">
                Country
              </label>
              <select
                id="country"
                value={selectedCountry}
                onChange={(e) => handleCountryChange(e.target.value)}
                className="form-control"
              >
                <option value="">Select a country...</option>
                {countries.map(country => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="taxType">
                Tax Type
              </label>
              <select
                id="taxType"
                value={taxType}
                onChange={(e) => setTaxType(e.target.value)}
                className="form-control"
              >
                <option value="vat">VAT / Sales Tax (Default)</option>
                <option value="corporate">Corporate Tax</option>
                <option value="personal">Personal Income Tax</option>
              </select>
              <small className="form-hint">Select the tax type to calculate</small>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="amount">
              Amount ({currencyCode})
            </label>
            <input
              type="number"
              id="amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={`Enter amount in ${currencyCode}...`}
              className="form-control"
              min="0"
              step="0.01"
            />
          </div>

          <button onClick={handleCalculate} className="btn-primary btn-large">
            Calculate Tax
          </button>
        </div>
      </div>

      {/* Results */}
      {result && result.success && (
        <div className="results-section">
          <div className="result-card main-result">
            <div className="result-header">
              <h2>Tax Calculation Result</h2>
              {result.aiVerified && (
                <span className="ai-verified-badge">
                  AI Verified
                </span>
              )}
            </div>

            <div className="result-details">
              <div className="country-info">
                <div className="result-item">
                  <span className="result-label">Country:</span>
                  <span className="result-value">
                    {result.country} ({result.countryCode})
                  </span>
                </div>
                <div className="result-item">
                  <span className="result-label">Tax Type:</span>
                  <span className="result-value">{result.taxType.toUpperCase()}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Tax Rate:</span>
                  <span className="result-value highlight">{result.taxRate}%</span>
                </div>
              </div>

              {result.notes && (
                <div className="tax-notes">
                   <em>{result.notes}</em>
                </div>
              )}

              <div className="result-divider"></div>

              <div className="calculation-breakdown">
                <h3>Calculation Breakdown</h3>
                <div className="formula-display">
                  <code>{result.calculation.formula}</code>
                </div>

                <div className="result-item large">
                  <span className="result-label">Original Amount:</span>
                  <span className="result-value">{currencySymbol}{result.amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                </div>
                <div className="result-item large">
                  <span className="result-label">Tax Amount:</span>
                  <span className="result-value tax-amount">{currencySymbol}{result.taxAmount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                </div>

                {taxType === 'vat' ? (
                  <div className="result-item large primary">
                    <span className="result-label">Total (with tax):</span>
                    <span className="result-value">{currencySymbol}{result.totalWithTax.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                  </div>
                ) : (
                  <div className="result-item large primary">
                    <span className="result-label">Net Amount (after tax):</span>
                    <span className="result-value">{currencySymbol}{result.netAfterTax.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                  </div>
                )}
              </div>

              <div className="result-footer">
                <div className="footer-info">
                  <span>
                    Last updated: {result.lastUpdated}
                  </span>
                  {result.aiVerified && (
                    <span className="verified-tag">AI Verified Tax Rate
                    </span>
                  )}
                </div>
                <small>Last updated: {result.lastUpdated}</small>
              </div>
            </div>
          </div>

          {/* AI Suggestions */}
          {suggestions.length > 0 && (
            <div className="suggestions-card">
              <h2>AI-Powered Insights</h2>
              <div className="suggestions-list">
                {suggestions.map((suggestion, index) => (
                  <div key={index} className={`suggestion-item ${suggestion.type}`}>
                    {getSuggestionIcon(suggestion.type)}
                    <div className="suggestion-content">
                      <h4>{suggestion.title}</h4>
                      <p>{suggestion.message}</p>
                      {suggestion.recommendation && (
                        <p className="suggestion-recommendation">
                           {suggestion.recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tax-Friendly Alternatives */}
          {alternatives.length > 0 && (
            <div className="alternatives-card">
              <h2>Tax-Friendly Alternatives</h2>
              <p className="alternatives-intro">Based on your selection, these countries offer lower {taxType} tax rates:
              </p>
              <div className="alternatives-list">
                {alternatives.map((alt, index) => (
                  <div key={index} className="alternative-item">
                    <div className="alternative-rank">#{index + 1}</div>
                    <div className="alternative-info">
                      <h4>{alt.country}</h4>
                      <div className="alternative-rate">{alt.rate}%</div>
                    </div>
                    <div className="alternative-savings">
                      <span className="savings-label">Potential Savings:</span>
                      <span className="savings-value">
                        {((result.taxRate - alt.rate) / result.taxRate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Country Comparison Tool */}
      <div className="comparison-section">
        <h2>Compare Countries</h2>
        <p>Select up to 5 countries to compare their tax rates</p>

        <div className="comparison-selector">
          <select
            onChange={(e) => {
              if (e.target.value) {
                addCompareCountry(e.target.value);
                e.target.value = '';
              }
            }}
            className="form-control"
          >
            <option value="">Add country to compare...</option>
            {countries.filter(c => !compareCountries.includes(c)).map(country => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
        </div>

        {compareCountries.length > 0 && (
          <div className="selected-countries">
            {compareCountries.map(country => (
              <div key={country} className="country-chip">
                {country}
                <button onClick={() => removeCompareCountry(country)} className="remove-btn">×</button>
              </div>
            ))}
          </div>
        )}

        {compareCountries.length > 0 && (
          <button onClick={handleCompare} className="btn-primary">
            Compare Tax Rates
          </button>
        )}

        {showComparison && compareCountries.length > 0 && (
          <div className="comparison-results">
            <h3>Comparison Results ({taxType})</h3>
            <div className="comparison-table">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Country</th>
                    <th>Tax Rate</th>
                    <th>On {currencySymbol}{amount || '0'}</th>
                  </tr>
                </thead>
                <tbody>
                  {getComparisonData().map((item, index) => (
                    <tr key={item.country}>
                      <td className="rank-cell">#{index + 1}</td>
                      <td className="country-cell">{item.country}</td>
                      <td className="rate-cell">{item.rate}%</td>
                      <td className="amount-cell">
                        {currencySymbol}{amount ? ((parseFloat(amount) * item.rate) / 100).toLocaleString() : '0'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* API Information for Developers */}
      <div className="api-section">
        <h2>API Integration</h2>
        <p className="api-intro">This calculator is built with a modular, API-ready architecture following the Ledgora specification.
        </p>
        <div className="api-endpoints">
          <h3>Available Endpoints (Future)</h3>
          <div className="endpoint-list">
            <div className="endpoint-item">
              <code>GET /api/tax/countries</code>
              <span>List all countries with tax rates</span>
            </div>
            <div className="endpoint-item">
              <code>GET /api/tax/calculate?country=ZA&amount=1000</code>
              <span>Calculate tax for specific amount</span>
            </div>
            <div className="endpoint-item">
              <code>POST /api/tax/update</code>
              <span>Admin: Update tax rates</span>
            </div>
            <div className="endpoint-item">
              <code>POST /api/tax/ai-verify</code>
              <span>AI validation endpoint</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tax Information */}
      <div className="info-section">
        <h2>About This Calculator</h2>
        <div className="info-grid">
          <div className="info-card">
            <h3>Global Coverage</h3>
            <p>Tax rates for 60+ countries including all major economies and tax havens</p>
          </div>
          <div className="info-card">
            <h3>AI-Powered</h3>
            <p>Intelligent suggestions for tax optimization and jurisdiction selection</p>
          </div>
          <div className="info-card">
            <h3>Multiple Tax Types</h3>
            <p>Corporate tax, personal income tax, and VAT/sales tax calculations</p>
          </div>
          <div className="info-card">
            <h3>Regular Updates</h3>
            <p>Tax rates updated regularly to reflect global tax law changes</p>
          </div>
        </div>
        <div className="disclaimer">
          <p>
            <strong>Disclaimer:</strong>This calculator provides estimates based on standard tax rates.
            Actual tax liability may vary based on deductions, credits, and specific circumstances.
            Consult with a qualified tax professional for accurate advice.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TaxCalculator;
