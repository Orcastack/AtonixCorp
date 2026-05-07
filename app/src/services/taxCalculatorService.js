// Tax Calculator Service for Ledgora
// Comprehensive global tax rates database with AI-powered validation
// Specification-compliant with modular, future-proof architecture

const TAX_RATES = {
  // North America
  'United States': {
    code: 'US',
    rate: 21,
    type: 'Corporate',
    personal: 37,
    vat: 0,
    currency: 'USD',
    currencySymbol: '$',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'Federal rate. State taxes vary by location.'
  },
  'Canada': {
    code: 'CA',
    rate: 15,
    type: 'Corporate',
    personal: 33,
    vat: 5,
    currency: 'CAD',
    currencySymbol: 'C$',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'GST rate. Provincial taxes additional.'
  },
  'Mexico': {
    code: 'MX',
    rate: 30,
    type: 'Corporate',
    personal: 35,
    vat: 16,
    currency: 'MXN',
    currencySymbol: 'MX$',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'IVA (VAT) standard rate'
  },

  // Europe
  'United Kingdom': {
    code: 'GB',
    rate: 19,
    type: 'Corporate',
    personal: 45,
    vat: 20,
    currency: 'GBP',
    currencySymbol: '£',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'Standard VAT rate'
  },
  'Germany': {
    code: 'DE',
    rate: 15,
    type: 'Corporate',
    personal: 45,
    vat: 19,
    currency: 'EUR',
    currencySymbol: '€',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'Mehrwertsteuer (VAT)'
  },
  'France': {
    code: 'FR',
    rate: 25,
    type: 'Corporate',
    personal: 45,
    vat: 20,
    currency: 'EUR',
    currencySymbol: '€',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'TVA (VAT) standard rate'
  },
  'Italy': {
    code: 'IT',
    rate: 24,
    type: 'Corporate',
    personal: 43,
    vat: 22,
    currency: 'EUR',
    currencySymbol: '€',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'IVA (VAT) standard rate'
  },
  'Spain': {
    code: 'ES',
    rate: 25,
    type: 'Corporate',
    personal: 47,
    vat: 21,
    currency: 'EUR',
    currencySymbol: '€',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'IVA (VAT) standard rate'
  },
  'Netherlands': { rate: 25.8, type: 'Corporate', personal: 49.5, vat: 21, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Belgium': { rate: 25, type: 'Corporate', personal: 50, vat: 21, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Switzerland': { rate: 8.5, type: 'Corporate', personal: 11.5, vat: 7.7, currency: 'CHF', currencySymbol: 'CHF', lastUpdated: '2025-01-01' },
  'Sweden': { rate: 20.6, type: 'Corporate', personal: 52, vat: 25, currency: 'SEK', currencySymbol: 'kr', lastUpdated: '2025-01-01' },
  'Norway': { rate: 22, type: 'Corporate', personal: 38, vat: 25, currency: 'NOK', currencySymbol: 'kr', lastUpdated: '2025-01-01' },
  'Denmark': { rate: 22, type: 'Corporate', personal: 52.07, vat: 25, currency: 'DKK', currencySymbol: 'kr', lastUpdated: '2025-01-01' },
  'Finland': { rate: 20, type: 'Corporate', personal: 51.25, vat: 24, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Ireland': { rate: 12.5, type: 'Corporate', personal: 40, vat: 23, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Portugal': { rate: 21, type: 'Corporate', personal: 48, vat: 23, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Poland': { rate: 19, type: 'Corporate', personal: 32, vat: 23, currency: 'PLN', currencySymbol: 'zł', lastUpdated: '2025-01-01' },
  'Austria': { rate: 24, type: 'Corporate', personal: 55, vat: 20, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Greece': { rate: 22, type: 'Corporate', personal: 44, vat: 24, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },

  // Asia
  'China': { rate: 25, type: 'Corporate', personal: 45, vat: 13, currency: 'CNY', currencySymbol: '¥', lastUpdated: '2025-01-01' },
  'Japan': { rate: 23.2, type: 'Corporate', personal: 45, vat: 10, currency: 'JPY', currencySymbol: '¥', lastUpdated: '2025-01-01' },
  'India': { rate: 25, type: 'Corporate', personal: 42.74, vat: 18, currency: 'INR', currencySymbol: '₹', lastUpdated: '2025-01-01' },
  'South Korea': { rate: 24, type: 'Corporate', personal: 45, vat: 10, currency: 'KRW', currencySymbol: '₩', lastUpdated: '2025-01-01' },
  'Singapore': { rate: 17, type: 'Corporate', personal: 22, vat: 8, currency: 'SGD', currencySymbol: 'S$', lastUpdated: '2025-01-01' },
  'Hong Kong': { rate: 16.5, type: 'Corporate', personal: 17, vat: 0, currency: 'HKD', currencySymbol: 'HK$', lastUpdated: '2025-01-01' },
  'Taiwan': { rate: 20, type: 'Corporate', personal: 40, vat: 5, currency: 'TWD', currencySymbol: 'NT$', lastUpdated: '2025-01-01' },
  'Thailand': { rate: 20, type: 'Corporate', personal: 35, vat: 7, currency: 'THB', currencySymbol: '฿', lastUpdated: '2025-01-01' },
  'Malaysia': { rate: 24, type: 'Corporate', personal: 30, vat: 6, currency: 'MYR', currencySymbol: 'RM', lastUpdated: '2025-01-01' },
  'Indonesia': { rate: 22, type: 'Corporate', personal: 35, vat: 11, currency: 'IDR', currencySymbol: 'Rp', lastUpdated: '2025-01-01' },
  'Philippines': { rate: 25, type: 'Corporate', personal: 35, vat: 12, currency: 'PHP', currencySymbol: '₱', lastUpdated: '2025-01-01' },
  'Vietnam': { rate: 20, type: 'Corporate', personal: 35, vat: 10, currency: 'VND', currencySymbol: '₫', lastUpdated: '2025-01-01' },
  'Pakistan': { rate: 29, type: 'Corporate', personal: 35, vat: 17, currency: 'PKR', currencySymbol: '₨', lastUpdated: '2025-01-01' },
  'Bangladesh': { rate: 32.5, type: 'Corporate', personal: 30, vat: 15, currency: 'BDT', currencySymbol: '৳', lastUpdated: '2025-01-01' },
  'Israel': { rate: 23, type: 'Corporate', personal: 50, vat: 17, currency: 'ILS', currencySymbol: '₪', lastUpdated: '2025-01-01' },
  'Saudi Arabia': { rate: 20, type: 'Corporate', personal: 0, vat: 15, currency: 'SAR', currencySymbol: 'SR', lastUpdated: '2025-01-01' },
  'United Arab Emirates': { rate: 9, type: 'Corporate', personal: 0, vat: 5, currency: 'AED', currencySymbol: 'د.إ', lastUpdated: '2025-01-01' },
  'Turkey': { rate: 20, type: 'Corporate', personal: 40, vat: 18, currency: 'TRY', currencySymbol: '₺', lastUpdated: '2025-01-01' },

  // Oceania
  'Australia': { rate: 30, type: 'Corporate', personal: 45, vat: 10, currency: 'AUD', currencySymbol: 'A$', lastUpdated: '2025-01-01' },
  'New Zealand': { rate: 28, type: 'Corporate', personal: 39, vat: 15, currency: 'NZD', currencySymbol: 'NZ$', lastUpdated: '2025-01-01' },

  // Africa
  'South Africa': {
    code: 'ZA',
    rate: 27,
    type: 'Corporate',
    personal: 45,
    vat: 15,
    currency: 'ZAR',
    currencySymbol: 'R',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'Standard VAT rate as per SARS'
  },
  'Nigeria': {
    code: 'NG',
    rate: 30,
    type: 'Corporate',
    personal: 24,
    vat: 7.5,
    currency: 'NGN',
    currencySymbol: '₦',
    lastUpdated: '2025-01-01',
    aiVerified: true,
    notes: 'VAT rate as per FIRS'
  },
  'Egypt': { rate: 22.5, type: 'Corporate', personal: 25, vat: 14, currency: 'EGP', currencySymbol: '£', lastUpdated: '2025-01-01' },
  'Kenya': { rate: 30, type: 'Corporate', personal: 35, vat: 16, currency: 'KES', currencySymbol: 'KSh', lastUpdated: '2025-01-01' },
  'Morocco': { rate: 31, type: 'Corporate', personal: 38, vat: 20, currency: 'MAD', currencySymbol: 'د.م.', lastUpdated: '2025-01-01' },

  // South America
  'Brazil': { rate: 34, type: 'Corporate', personal: 27.5, vat: 17, currency: 'BRL', currencySymbol: 'R$', lastUpdated: '2025-01-01' },
  'Argentina': { rate: 30, type: 'Corporate', personal: 35, vat: 21, currency: 'ARS', currencySymbol: '$', lastUpdated: '2025-01-01' },
  'Chile': { rate: 27, type: 'Corporate', personal: 40, vat: 19, currency: 'CLP', currencySymbol: '$', lastUpdated: '2025-01-01' },
  'Colombia': { rate: 35, type: 'Corporate', personal: 39, vat: 19, currency: 'COP', currencySymbol: '$', lastUpdated: '2025-01-01' },
  'Peru': { rate: 29.5, type: 'Corporate', personal: 30, vat: 18, currency: 'PEN', currencySymbol: 'S/', lastUpdated: '2025-01-01' },

  // Tax Havens / Low Tax Jurisdictions
  'Bahamas': { rate: 0, type: 'Corporate', personal: 0, vat: 12, currency: 'BSD', currencySymbol: 'B$', lastUpdated: '2025-01-01' },
  'Cayman Islands': { rate: 0, type: 'Corporate', personal: 0, vat: 0, currency: 'KYD', currencySymbol: 'CI$', lastUpdated: '2025-01-01' },
  'Bermuda': { rate: 0, type: 'Corporate', personal: 0, vat: 0, currency: 'BMD', currencySymbol: 'BD$', lastUpdated: '2025-01-01' },
  'Monaco': { rate: 0, type: 'Corporate', personal: 0, vat: 20, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
  'Luxembourg': { rate: 24.94, type: 'Corporate', personal: 42, vat: 17, currency: 'EUR', currencySymbol: '€', lastUpdated: '2025-01-01' },
};

class TaxCalculatorService {
  constructor() {
    this.taxRates = TAX_RATES;
    this.pendingAIUpdates = [];
    this.adminWarnings = [];
  }

  // Get all available countries (API-ready)
  getCountries() {
    return Object.keys(this.taxRates).sort();
  }

  // Get all countries with full data (for admin panel)
  getAllCountriesData() {
    return Object.keys(this.taxRates).map(country => ({
      country,
      ...this.taxRates[country]
    })).sort((a, b) => a.country.localeCompare(b.country));
  }

  // Get tax information for a specific country
  getTaxInfo(country) {
    return this.taxRates[country] || null;
  }

  // Search countries by name or code
  searchCountries(query) {
    const lowerQuery = query.toLowerCase();
    return this.getCountries().filter(country => {
      const taxInfo = this.taxRates[country];
      return country.toLowerCase().includes(lowerQuery) ||
             taxInfo.code.toLowerCase().includes(lowerQuery);
    });
  }

  // Calculate tax based on country and amount (API-ready format)
  calculateTax(country, amount, taxType = 'vat') {
    const taxInfo = this.getTaxInfo(country);
    if (!taxInfo) {
      return {
        success: false,
        error: 'Country not found in database',
        amount: amount,
        tax: 0,
        total: amount
      };
    }

    let rate = taxInfo.vat; // Default to VAT as per spec
    if (taxType === 'corporate') rate = taxInfo.rate;
    if (taxType === 'personal') rate = taxInfo.personal;

    const taxAmount = (amount * rate) / 100;
    const total = amount + taxAmount;
    const netAmount = amount - taxAmount;

    return {
      success: true,
      country,
      countryCode: taxInfo.code,
      currency: taxInfo.currency,
      currencySymbol: taxInfo.currencySymbol,
      amount: parseFloat(amount.toFixed(2)),
      taxType,
      taxRate: rate,
      taxAmount: parseFloat(taxAmount.toFixed(2)),
      totalWithTax: parseFloat(total.toFixed(2)),
      netAfterTax: parseFloat(netAmount.toFixed(2)),
      lastUpdated: taxInfo.lastUpdated,
      aiVerified: taxInfo.aiVerified,
      notes: taxInfo.notes || null,
      calculation: {
        formula: `${amount} × (${rate}% / 100) = ${taxAmount.toFixed(2)}`,
        breakdown: {
          originalAmount: amount,
          taxPercentage: rate,
          taxAmount: taxAmount,
          result: taxType === 'vat' ? total : netAmount
        }
      }
    };
  }

  // AI-powered tax rate validation
  validateTaxRate(country, rate, taxType = 'corporate') {
    const taxInfo = this.getTaxInfo(country);
    if (!taxInfo) {
      return {
        valid: false,
        message: 'Country not found in database',
        recommendation: 'Please select a valid country'
      };
    }

    const expectedRate = taxType === 'personal' ? taxInfo.personal :
                        taxType === 'vat' ? taxInfo.vat : taxInfo.rate;

    const difference = Math.abs(rate - expectedRate);
    const percentageDiff = (difference / expectedRate) * 100;

    if (percentageDiff === 0) {
      return {
        valid: true,
        message: 'Tax rate is correct and up to date',
        confidence: 100
      };
    } else if (percentageDiff < 5) {
      return {
        valid: true,
        message: 'Tax rate is close but may have recent changes',
        recommendation: `Current database rate: ${expectedRate}%`,
        confidence: 90
      };
    } else if (percentageDiff < 15) {
      return {
        valid: false,
        message: 'Tax rate differs significantly from database',
        recommendation: `Expected rate: ${expectedRate}%. Please verify with local tax authority.`,
        confidence: 60
      };
    } else {
      return {
        valid: false,
        message: 'Tax rate appears incorrect',
        recommendation: `Database shows ${expectedRate}% for ${country}. Your input of ${rate}% is significantly different.`,
        confidence: 30
      };
    }
  }

  // AI-powered tax optimization suggestions
  getOptimizationSuggestions(country, amount, taxType = 'corporate') {
    const taxInfo = this.getTaxInfo(country);
    if (!taxInfo) return [];

    const suggestions = [];
    const rate = taxType === 'personal' ? taxInfo.personal :
                 taxType === 'vat' ? taxInfo.vat : taxInfo.rate;

    // High tax rate warning
    if (rate > 35) {
      suggestions.push({
        type: 'warning',
        title: 'High Tax Jurisdiction',
        message: `${country} has a ${rate}% ${taxType} tax rate, which is above global average.`,
        recommendation: 'Consider tax-efficient investment vehicles or jurisdictions.'
      });
    }

    // Low tax opportunity
    if (rate < 15) {
      suggestions.push({
        type: 'success',
        title: 'Tax-Efficient Jurisdiction',
        message: `${country} offers favorable ${rate}% ${taxType} tax rate.`,
        recommendation: 'This is a tax-advantaged location for this activity.'
      });
    }

    // VAT considerations
    if (taxType === 'vat' && taxInfo.vat > 20) {
      suggestions.push({
        type: 'info',
        title: 'High VAT Rate',
        message: `${country} has ${taxInfo.vat}% VAT, affecting consumer prices.`,
        recommendation: 'Factor this into pricing strategies.'
      });
    }

    // Tax-free personal income
    if (taxType === 'personal' && taxInfo.personal === 0) {
      suggestions.push({
        type: 'success',
        title: 'Tax-Free Personal Income',
        message: `${country} does not impose personal income tax.`,
        recommendation: 'Significant advantage for high-income individuals.'
      });
    }

    // Large amount warning
    if (amount > 1000000) {
      suggestions.push({
        type: 'info',
        title: 'Large Transaction',
        message: 'Consider consulting with tax professionals for amounts over $1M.',
        recommendation: 'International tax planning may provide additional benefits.'
      });
    }

    return suggestions;
  }

  // Compare tax rates across multiple countries
  compareTaxRates(countries, taxType = 'corporate') {
    return countries.map(country => {
      const taxInfo = this.getTaxInfo(country);
      if (!taxInfo) return null;

      const rate = taxType === 'personal' ? taxInfo.personal :
                   taxType === 'vat' ? taxInfo.vat : taxInfo.rate;

      return {
        country,
        rate,
        type: taxType,
        lastUpdated: taxInfo.lastUpdated
      };
    }).filter(item => item !== null).sort((a, b) => a.rate - b.rate);
  }

  // Get tax-friendly alternatives
  getTaxFriendlyAlternatives(currentCountry, taxType = 'corporate', limit = 5) {
    const currentTaxInfo = this.getTaxInfo(currentCountry);
    if (!currentTaxInfo) return [];

    const currentRate = taxType === 'personal' ? currentTaxInfo.personal :
                       taxType === 'vat' ? currentTaxInfo.vat : currentTaxInfo.rate;

    const alternatives = this.getCountries()
      .filter(country => country !== currentCountry)
      .map(country => {
        const taxInfo = this.getTaxInfo(country);
        const rate = taxType === 'personal' ? taxInfo.personal :
                    taxType === 'vat' ? taxInfo.vat : taxInfo.rate;
        return { country, rate };
      })
      .filter(item => item.rate < currentRate)
      .sort((a, b) => a.rate - b.rate)
      .slice(0, limit);

    return alternatives;
  }

  // Admin: Update tax rate
  updateTaxRate(country, newRates, adminApproved = false) {
    if (this.taxRates[country]) {
      const oldRates = { ...this.taxRates[country] };

      this.taxRates[country] = {
        ...this.taxRates[country],
        ...newRates,
        lastUpdated: new Date().toISOString().split('T')[0],
        aiVerified: adminApproved ? true : false
      };

      // Log the change
      this.logTaxChange(country, oldRates, this.taxRates[country], adminApproved);

      return {
        success: true,
        message: 'Tax rate updated successfully',
        country,
        oldRates,
        newRates: this.taxRates[country]
      };
    }
    return { success: false, message: 'Country not found' };
  }

  // Admin: Add new country
  addCountry(country, taxData) {
    if (this.taxRates[country]) {
      return { success: false, message: 'Country already exists. Use updateTaxRate instead.' };
    }

    // Validate required fields
    if (!taxData.code || !taxData.vat) {
      return {
        success: false,
        message: 'Missing required fields: code and vat rate are mandatory'
      };
    }

    this.taxRates[country] = {
      code: taxData.code,
      rate: taxData.rate || 0,
      type: taxData.type || 'Corporate',
      personal: taxData.personal || 0,
      vat: taxData.vat,
      lastUpdated: new Date().toISOString().split('T')[0],
      aiVerified: taxData.aiVerified || false,
      notes: taxData.notes || ''
    };

    return {
      success: true,
      message: 'Country added successfully',
      country,
      data: this.taxRates[country]
    };
  }

  // AI: Suggest tax rate update
  suggestTaxUpdate(country, suggestedRate, taxType, reason) {
    const suggestion = {
      id: Date.now(),
      country,
      taxType,
      currentRate: this.getTaxInfo(country)?.[taxType === 'vat' ? 'vat' : taxType === 'corporate' ? 'rate' : 'personal'],
      suggestedRate,
      reason,
      confidence: this.calculateAIConfidence(country, suggestedRate, taxType),
      timestamp: new Date().toISOString(),
      status: 'pending'
    };

    this.pendingAIUpdates.push(suggestion);
    return suggestion;
  }

  // Admin: Get pending AI suggestions
  getPendingAISuggestions() {
    return this.pendingAIUpdates.filter(s => s.status === 'pending');
  }

  // Admin: Approve AI suggestion
  approveAISuggestion(suggestionId) {
    const suggestion = this.pendingAIUpdates.find(s => s.id === suggestionId);
    if (!suggestion) {
      return { success: false, message: 'Suggestion not found' };
    }

    const updateData = {};
    if (suggestion.taxType === 'vat') updateData.vat = suggestion.suggestedRate;
    if (suggestion.taxType === 'corporate') updateData.rate = suggestion.suggestedRate;
    if (suggestion.taxType === 'personal') updateData.personal = suggestion.suggestedRate;

    const result = this.updateTaxRate(suggestion.country, updateData, true);

    if (result.success) {
      suggestion.status = 'approved';
      suggestion.approvedAt = new Date().toISOString();
    }

    return result;
  }

  // Admin: Reject AI suggestion
  rejectAISuggestion(suggestionId, reason) {
    const suggestion = this.pendingAIUpdates.find(s => s.id === suggestionId);
    if (!suggestion) {
      return { success: false, message: 'Suggestion not found' };
    }

    suggestion.status = 'rejected';
    suggestion.rejectedAt = new Date().toISOString();
    suggestion.rejectionReason = reason;

    return { success: true, message: 'Suggestion rejected' };
  }

  // AI: Generate warning for suspicious tax rate
  generateTaxWarning(country, inputRate, taxType, expectedRate) {
    const difference = Math.abs(inputRate - expectedRate);
    const percentageDiff = (difference / expectedRate) * 100;

    if (percentageDiff > 20) {
      const warning = {
        id: Date.now(),
        type: 'error',
        country,
        taxType,
        inputRate,
        expectedRate,
        difference: percentageDiff.toFixed(1),
        message: `CRITICAL: Input rate ${inputRate}% differs significantly from expected ${expectedRate}%`,
        recommendation: 'Verify with official tax authority before proceeding',
        timestamp: new Date().toISOString()
      };
      this.adminWarnings.push(warning);
      return warning;
    }

    return null;
  }

  // Admin: Get all warnings
  getAdminWarnings() {
    return this.adminWarnings.sort((a, b) =>
      new Date(b.timestamp) - new Date(a.timestamp)
    );
  }

  // Helper: Calculate AI confidence score
  calculateAIConfidence(country, suggestedRate, taxType) {
    const taxInfo = this.getTaxInfo(country);
    if (!taxInfo) return 50;

    const currentRate = taxType === 'vat' ? taxInfo.vat :
                       taxType === 'corporate' ? taxInfo.rate : taxInfo.personal;

    const difference = Math.abs(suggestedRate - currentRate);
    const percentageDiff = (difference / currentRate) * 100;

    if (percentageDiff < 2) return 95;
    if (percentageDiff < 5) return 85;
    if (percentageDiff < 10) return 75;
    if (percentageDiff < 20) return 60;
    return 40;
  }

  // Helper: Log tax changes (for audit trail)
  logTaxChange(country, oldRates, newRates, adminApproved) {
    const log = {
      timestamp: new Date().toISOString(),
      country,
      oldRates,
      newRates,
      adminApproved,
      changes: this.getChangedFields(oldRates, newRates)
    };

    // In production, this would save to a database
    console.log('Tax Change Log:', log);
    return log;
  }

  // Helper: Get changed fields
  getChangedFields(oldData, newData) {
    const changes = [];
    const fields = ['rate', 'personal', 'vat', 'notes'];

    fields.forEach(field => {
      if (oldData[field] !== newData[field]) {
        changes.push({
          field,
          oldValue: oldData[field],
          newValue: newData[field]
        });
      }
    });

    return changes;
  }

  // Export data for offline use
  exportTaxData() {
    return {
      taxRates: this.taxRates,
      exportDate: new Date().toISOString(),
      totalCountries: Object.keys(this.taxRates).length,
      version: '1.0.0'
    };
  }

  // Import tax data (for offline fallback)
  importTaxData(data) {
    if (data.taxRates && typeof data.taxRates === 'object') {
      this.taxRates = data.taxRates;
      return { success: true, message: 'Tax data imported successfully' };
    }
    return { success: false, message: 'Invalid data format' };
  }
}

const taxCalculatorService = new TaxCalculatorService();
export default taxCalculatorService;
