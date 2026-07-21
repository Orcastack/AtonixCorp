import React, { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';
import calculationEngine from '../services/calculation/calculationEngine';
import validationService from '../services/calculation/validationService';
import monthlyAnalysisService from '../services/calculation/monthlyAnalysisService';
import taxCalculatorService from '../services/taxCalculatorService';
import {
  modelTemplatesAPI, financialModelsAPI, scenariosAPI,
  aiInsightsAPI, reportsAPI,
  organizationsAPI, entitiesAPI, bankingTransactionsAPI
} from '../services/api';
import { getApiOrigin } from '../utils/apiBaseUrl';

const FinanceContext = createContext();

const portfolioData = [];
const EXPENSE_SOURCE_OPTIONS = [
  { value: 'all', label: 'All Sources' },
  { value: 'manual', label: 'Manual Only' },
  { value: 'imported', label: 'Imported Only' },
];

const normalizeExpenseSourceType = (sourceType) => {
  if (sourceType === 'bank_feed' || sourceType === 'imported') {
    return 'imported';
  }
  return 'manual';
};

const filterExpensesBySource = (items = [], sourceFilter = 'all') => {
  if (sourceFilter === 'all') {
    return items;
  }

  return items.filter((item) => normalizeExpenseSourceType(item.sourceType) === sourceFilter);
};

const buildMonthlyExpenseHistory = (items = [], incomes = []) => {
  const months = items.reduce((accumulator, item) => {
    if (!item.date) {
      return accumulator;
    }

    const date = new Date(item.date);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    if (!accumulator[key]) {
      accumulator[key] = {
        year: date.getFullYear(),
        month: date.getMonth(),
        expenses: 0,
        income: 0,
        sourceBreakdown: {
          manual: { source: 'manual', label: 'Manual entries', amount: 0, count: 0 },
          imported: { source: 'imported', label: 'Imported bank feed', amount: 0, count: 0 },
        },
      };
    }

    const source = normalizeExpenseSourceType(item.sourceType);
    const amount = parseFloat(item.amount || 0);
    accumulator[key].expenses = calculationEngine.round(accumulator[key].expenses + amount);
    accumulator[key].sourceBreakdown[source].amount = calculationEngine.round(
      accumulator[key].sourceBreakdown[source].amount + amount
    );
    accumulator[key].sourceBreakdown[source].count += 1;

    return accumulator;
  }, {});

  incomes.forEach((item) => {
    if (!item.date) {
      return;
    }

    const date = new Date(item.date);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    if (!months[key]) {
      months[key] = {
        year: date.getFullYear(),
        month: date.getMonth(),
        expenses: 0,
        income: 0,
        sourceBreakdown: {
          manual: { source: 'manual', label: 'Manual entries', amount: 0, count: 0 },
          imported: { source: 'imported', label: 'Imported bank feed', amount: 0, count: 0 },
        },
      };
    }

    months[key].income = calculationEngine.round(
      months[key].income + parseFloat(item.amount || 0)
    );
  });

  return Object.values(months);
};

export const FinanceProvider = ({ children }) => {
  // Core Data States
  const [expenses, setExpenses] = useState([]);
  const [bankFeedExpenses, setBankFeedExpenses] = useState([]);
  const [income, setIncome] = useState([]);
  const [budgets, setBudgets] = useState([]);

  const API_BASE_URL = getApiOrigin();

  const apiUrl = useCallback(
    (path) => {
      if (!path) return API_BASE_URL;
      if (path.startsWith('http://') || path.startsWith('https://')) return path;
      return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
    },
    [API_BASE_URL]
  );

  const buildAuthHeaders = useCallback(() => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  // Financial Modeling States
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState(null);
  const [modelTemplates, setModelTemplates] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [sensitivityAnalyses, setSensitivityAnalyses] = useState([]);
  const [aiInsights, setAiInsights] = useState([]);
  const [customKPIs, setCustomKPIs] = useState([]);
  const [reports, setReports] = useState([]);
  const [consolidations, setConsolidations] = useState([]);
  const [taxCalculations, setTaxCalculations] = useState([]);
  const [complianceDeadlines, setComplianceDeadlines] = useState([]);
  const [cashflowForecasts, setCashflowForecasts] = useState([]);

  // Enterprise States
  const [organizations, setOrganizations] = useState([]);
  const [entities, setEntities] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [taxExposures, setTaxExposures] = useState([]);

  // Loading and Error States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // User Settings
  const [userCountry, setUserCountry] = useState('United States');
  const [userTaxRate, setUserTaxRate] = useState(21); // Default corporate tax
  const [userTaxType, setUserTaxType] = useState('corporate');

  // Monthly Tracking
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const current = monthlyAnalysisService.getCurrentMonth();
    return { year: current.year, month: current.month };
  });
  const [availableMonths, setAvailableMonths] = useState([]);
  const [expenseSourceFilter, setExpenseSourceFilter] = useState('all');

  // Calculated States (auto-updated by engine)
  const [financialSummary, setFinancialSummary] = useState(null);
  const [monthlySummary, setMonthlySummary] = useState(null);
  const [validationResults, setValidationResults] = useState(null);

  const mapBankTransactionToExpense = useCallback((transaction) => {
    const numericAmount = Math.abs(parseFloat(transaction.amount || 0));
    const transactionDate = transaction.transaction_date || transaction.date || new Date().toISOString();
    return {
      id: `bank-${transaction.id}`,
      bankingTransactionId: transaction.id,
      description: transaction.merchant_name || transaction.description || 'Imported bank transaction',
      amount: numericAmount,
      category: transaction.normalized_category || transaction.raw_category || 'Uncategorized',
      date: transactionDate,
      sourceType: 'bank_feed',
      sourceLabel: 'Bank Feed',
      bankAccountName: transaction.bank_account_name || '',
      dashboardBucket: transaction.dashboard_bucket || 'Needs Review',
      canDelete: false,
      originalAmount: parseFloat(transaction.amount || 0),
      metadata: transaction,
    };
  }, []);

  const mergedExpenses = useMemo(
    () => [
      ...(Array.isArray(expenses) ? expenses.map((expense) => ({ ...expense, sourceType: expense.sourceType || 'manual', sourceLabel: expense.sourceLabel || 'Manual', canDelete: expense.canDelete !== false })) : []),
      ...(Array.isArray(bankFeedExpenses) ? bankFeedExpenses : []),
    ],
    [bankFeedExpenses, expenses]
  );

  const filteredExpenses = useMemo(
    () => filterExpensesBySource(mergedExpenses, expenseSourceFilter),
    [expenseSourceFilter, mergedExpenses]
  );

  const historicalExpenseData = useMemo(() => {
    return buildMonthlyExpenseHistory(filteredExpenses, income).filter(
      (entry) => !(entry.year === selectedMonth.year && entry.month === selectedMonth.month)
    );
  }, [filteredExpenses, income, selectedMonth.month, selectedMonth.year]);

  // ==================== CALCULATION ENGINE ====================

  /**
   * Master recalculation function
   * Called automatically when any financial data changes
   */
  const recalculateAll = useCallback(() => {
    // Get tax info for user's country
    const taxInfo = taxCalculatorService.getTaxInfo(userCountry);
    const effectiveTaxRate = userTaxRate || (taxInfo ? taxInfo.rate : 0);

    // Transform income data to match calculator format
    const transformedIncome = income.map(item => ({
      amount: parseFloat(item.amount || 0),
      category: item.source || 'Other',
      date: item.date
    }));

    // Calculate complete financial summary using engine
    const summary = calculationEngine.calculateFinancialSummary({
      incomes: transformedIncome,
      expenses: filteredExpenses,
      budgets: budgets,
      taxRate: effectiveTaxRate,
      country: userCountry
    });

    setFinancialSummary(summary);

    // Calculate monthly summary for selected month
    const monthly = monthlyAnalysisService.generateMonthlySummary({
      incomes: transformedIncome,
      expenses: filteredExpenses,
      budgets: budgets,
      year: selectedMonth.year,
      month: selectedMonth.month,
      taxRate: effectiveTaxRate,
      country: userCountry
    });

    setMonthlySummary(monthly);

    // Validate all data
    const validation = validationService.validateAllFinancialData({
      totalIncome: summary.income.gross,
      totalExpenses: summary.expenses.total,
      totalBudget: summary.budget.total,
      taxRate: effectiveTaxRate,
      country: userCountry,
      summary: summary,
      budgets,
      expenseTransactions: filteredExpenses,
      selectedMonth,
      historicalExpenseData,
      monthlyIncome: monthly.totals?.totalIncome || 0,
      expenseSourceFilter,
    });

    setValidationResults(validation);

    return summary;
  }, [budgets, expenseSourceFilter, filteredExpenses, historicalExpenseData, income, selectedMonth, userCountry, userTaxRate]);

  /**
   * Update available months based on existing transactions
   */
  const updateAvailableMonths = useCallback(() => {
    const months = new Set();

    // Get months from income
    income.forEach(item => {
      if (item.date) {
        const date = new Date(item.date);
        months.add(`${date.getFullYear()}-${date.getMonth()}`);
      }
    });

    // Get months from expenses
    mergedExpenses.forEach(item => {
      if (item.date) {
        const date = new Date(item.date);
        months.add(`${date.getFullYear()}-${date.getMonth()}`);
      }
    });

    // Convert to sorted array of {year, month} objects
    const monthsList = Array.from(months)
      .map(str => {
        const [year, month] = str.split('-');
        return { year: parseInt(year), month: parseInt(month) };
      })
      .sort((a, b) => {
        if (a.year !== b.year) return b.year - a.year; // Newest first
        return b.month - a.month;
      });

    // Always include current month
    const current = monthlyAnalysisService.getCurrentMonth();
    const currentExists = monthsList.some(m => m.year === current.year && m.month === current.month);
    if (!currentExists) {
      monthsList.unshift(current);
    }

    setAvailableMonths(monthsList);
  }, [income, mergedExpenses]);

  // Recalculate everything when data changes
  useEffect(() => {
    recalculateAll();
    updateAvailableMonths();
  }, [recalculateAll, updateAvailableMonths]);

  // Load persisted personal finance data for authenticated users
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setExpenses([]);
      setIncome([]);
      setBudgets([]);
      return;
    }

    const load = async () => {
      try {
        const [expRes, incRes, budRes, bankRes] = await Promise.all([
          fetch(apiUrl('/api/expenses/'), { headers: buildAuthHeaders() }),
          fetch(apiUrl('/api/income/'), { headers: buildAuthHeaders() }),
          fetch(apiUrl('/api/budgets/'), { headers: buildAuthHeaders() }),
          fetch(apiUrl('/api/banking-transactions/'), { headers: buildAuthHeaders() }),
        ]);

        const expJson = expRes.ok ? await expRes.json() : [];
        const incJson = incRes.ok ? await incRes.json() : [];
        const budJson = budRes.ok ? await budRes.json() : [];
        const bankJson = bankRes.ok ? await bankRes.json() : [];

        const expItems = Array.isArray(expJson) ? expJson : expJson.results || [];
        const incItems = Array.isArray(incJson) ? incJson : incJson.results || [];
        const budItems = Array.isArray(budJson) ? budJson : budJson.results || [];
        const bankItems = Array.isArray(bankJson) ? bankJson : bankJson.results || [];
        const importedExpenseItems = bankItems
          .filter((item) => parseFloat(item.amount || 0) < 0)
          .map(mapBankTransactionToExpense);

        setExpenses(expItems);
        setIncome(incItems);
        setBudgets(budItems);
        setBankFeedExpenses(importedExpenseItems);
      } catch (err) {
        console.error('Failed to load personal finance data:', err);
      }
    };

    load();
  }, [apiUrl, buildAuthHeaders, mapBankTransactionToExpense]);

  // Load persisted user settings (country/tax) for authenticated users
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const loadSettings = async () => {
      try {
        const res = await fetch(apiUrl('/api/auth/me/'), { headers: buildAuthHeaders() });
        if (!res.ok) return;
        const me = await res.json();

        if (me?.country) setUserCountry(me.country);
        if (typeof me?.tax_rate === 'number' && !Number.isNaN(me.tax_rate)) {
          setUserTaxRate(me.tax_rate);
        }
        if (me?.tax_type) setUserTaxType(me.tax_type);
      } catch (err) {
        console.error('Failed to load user settings:', err);
      }
    };

    loadSettings();
  }, [apiUrl, buildAuthHeaders]);

  /**
   * Change selected month
   */
  const changeMonth = (year, month) => {
    setSelectedMonth({ year, month });
  };

  // ==================== EXPENSES ====================

  const addExpense = async (expense) => {
    // Validate expense first
    const validation = validationService.validateExpense(
      expense.amount,
      expense.category,
      budgets.find(b => b.category === expense.category)?.limit
    );

    if (!validation.isValid) {
      console.error('Expense validation failed:', validation.errors);
      // Still add but warn user
      if (validation.warnings.length > 0) {
        console.warn('Expense warnings:', validation.warnings);
      }
    }

    try {
      const response = await fetch(apiUrl('/api/expenses/'), {
        method: 'POST',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description: expense.description,
          amount: calculationEngine.round(parseFloat(expense.amount || 0)),
          category: expense.category || 'Other',
          date: expense.date || new Date().toISOString().split('T')[0],
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create expense');
      }

      const created = await response.json();
      setExpenses((prev) => [created, ...(Array.isArray(prev) ? prev : [])]);

      // Refresh budgets because backend may update spent
      const budRes = await fetch(apiUrl('/api/budgets/'), { headers: buildAuthHeaders() });
      if (budRes.ok) {
        const budJson = await budRes.json();
        const budItems = Array.isArray(budJson) ? budJson : budJson.results || [];
        setBudgets(budItems);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteExpense = async (id) => {
    try {
      const response = await fetch(apiUrl(`/api/expenses/${id}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error('Failed to delete expense');
      }
      setExpenses((prev) => (Array.isArray(prev) ? prev.filter(e => e.id !== id) : []));
    } catch (err) {
      console.error(err);
    }
  };

  const updateExpense = (id, updatedExpense) => {
    setExpenses(expenses.map(e =>
      e.id === id
        ? { ...e, ...updatedExpense, amount: calculationEngine.round(parseFloat(updatedExpense.amount || e.amount)) }
        : e
    ));
  };

  // ==================== INCOME ====================

  const addIncome = async (incomeItem) => {
    // Validate income first
    const validation = validationService.validateIncome(
      incomeItem.amount,
      incomeItem.source
    );

    if (!validation.isValid) {
      console.error('Income validation failed:', validation.errors);
    }

    try {
      const response = await fetch(apiUrl('/api/income/'), {
        method: 'POST',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source: incomeItem.source || 'Other',
          amount: calculationEngine.round(parseFloat(incomeItem.amount || 0)),
          date: incomeItem.date || new Date().toISOString().split('T')[0],
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create income');
      }

      const created = await response.json();
      setIncome((prev) => [created, ...(Array.isArray(prev) ? prev : [])]);
    } catch (err) {
      console.error(err);
    }
  };

  const deleteIncome = async (id) => {
    try {
      const response = await fetch(apiUrl(`/api/income/${id}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error('Failed to delete income');
      }
      setIncome((prev) => (Array.isArray(prev) ? prev.filter(i => i.id !== id) : []));
    } catch (err) {
      console.error(err);
    }
  };

  const updateIncome = (id, updatedIncome) => {
    setIncome(income.map(i =>
      i.id === id
        ? { ...i, ...updatedIncome, amount: calculationEngine.round(parseFloat(updatedIncome.amount || i.amount)) }
        : i
    ));
  };

  // ==================== BUDGETS ====================

  const addBudget = async (budget) => {
    // Validate budget
    const validation = validationService.validateBudget(budget.amount || budget.limit);

    if (!validation.isValid) {
      console.error('Budget validation failed:', validation.errors);
    }

    try {
      const response = await fetch(apiUrl('/api/budgets/'), {
        method: 'POST',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          category: budget.category || 'Other',
          limit: calculationEngine.round(parseFloat(budget.amount || budget.limit || 0)),
          color: budget.color,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create budget');
      }

      const created = await response.json();
      setBudgets((prev) => [...(Array.isArray(prev) ? prev : []), created]);
    } catch (err) {
      console.error(err);
    }
  };

  const updateBudget = (id, updates) => {
    setBudgets(budgets.map(b =>
      b.id === id
        ? {
            ...b,
            ...updates,
            amount: updates.amount ? calculationEngine.round(parseFloat(updates.amount)) : b.amount,
            limit: updates.limit ? calculationEngine.round(parseFloat(updates.limit)) : b.limit
          }
        : b
    ));
  };

  const deleteBudget = async (id) => {
    try {
      const response = await fetch(apiUrl(`/api/budgets/${id}/`), {
        method: 'DELETE',
        headers: buildAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error('Failed to delete budget');
      }
      setBudgets((prev) => (Array.isArray(prev) ? prev.filter(b => b.id !== id) : []));
    } catch (err) {
      console.error(err);
    }
  };

  // ==================== CALCULATIONS (from engine) ====================

  // These use the calculation engine instead of manual calculations
  const totalIncome = financialSummary ? financialSummary.income.gross :
    calculationEngine.calculateTotalIncome(income.map(i => ({ amount: i.amount })));

  const totalExpenses = financialSummary ? financialSummary.expenses.total :
    calculationEngine.calculateTotalExpenses(filteredExpenses);

  const balance = financialSummary ? financialSummary.balance.net :
    calculationEngine.calculateNetBalance(totalIncome, totalExpenses);

  const netIncome = financialSummary ? financialSummary.income.net :
    calculationEngine.calculateNetIncome(totalIncome, userTaxRate);

  const taxAmount = financialSummary ? financialSummary.tax.amount :
    calculationEngine.calculateTax(totalIncome, userTaxRate);

  // ==================== API INTEGRATION FUNCTIONS ====================

  // Financial Modeling APIs
  const loadModelTemplates = async () => {
    try {
      setLoading(true);
      const response = await modelTemplatesAPI.getAll();
      setModelTemplates(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load model templates');
      console.error('Error loading model templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadFinancialModels = async () => {
    try {
      setLoading(true);
      const response = await financialModelsAPI.getAll();
      setModels(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load financial models');
      console.error('Error loading financial models:', err);
    } finally {
      setLoading(false);
    }
  };

  const createFinancialModel = async (modelData) => {
    try {
      setLoading(true);
      const response = await financialModelsAPI.create(modelData);
      setModels(prev => [...prev, response.data]);
      return response.data;
    } catch (err) {
      setError('Failed to create financial model');
      console.error('Error creating financial model:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const calculateFinancialModel = async (modelId) => {
    try {
      setLoading(true);
      const response = await financialModelsAPI.calculate(modelId);
      // Update the model in the list
      setModels(prev => prev.map(model =>
        model.id === modelId ? response.data : model
      ));
      return response.data;
    } catch (err) {
      setError('Failed to calculate financial model');
      console.error('Error calculating financial model:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const loadScenarios = async (modelId = null) => {
    try {
      setLoading(true);
      const response = await scenariosAPI.getAll();
      let scenarios = response.data.results || response.data;
      if (modelId) {
        scenarios = scenarios.filter(s => s.financial_model === modelId);
      }
      setScenarios(scenarios);
    } catch (err) {
      setError('Failed to load scenarios');
      console.error('Error loading scenarios:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAIInsights = async () => {
    try {
      setLoading(true);
      const response = await aiInsightsAPI.getAll();
      setAiInsights(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load AI insights');
      console.error('Error loading AI insights:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadReports = async () => {
    try {
      setLoading(true);
      const response = await reportsAPI.getAll();
      setReports(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load reports');
      console.error('Error loading reports:', err);
    } finally {
      setLoading(false);
    }
  };

  // Enterprise APIs
  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const response = await organizationsAPI.getAll();
      setOrganizations(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load organizations');
      console.error('Error loading organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadEntities = async () => {
    try {
      setLoading(true);
      const response = await entitiesAPI.getAll();
      setEntities(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load entities');
      console.error('Error loading entities:', err);
    } finally {
      setLoading(false);
    }
  };

  // ==================== TAX MANAGEMENT ====================

  const updateUserCountry = async (country) => {
    setUserCountry(country);

    // Keep local UX behavior: auto-suggest a default corporate rate for the selected country.
    const taxInfo = taxCalculatorService.getTaxInfo(country);
    if (taxInfo) {
      setUserTaxRate(taxInfo.rate);
    }

    try {
      const res = await fetch(apiUrl('/api/auth/me/'), {
        method: 'PATCH',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ country }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        console.error('Failed to persist country:', err || res.status);
      }
    } catch (err) {
      console.error('Failed to persist country:', err);
    }
  };

  const updateUserTaxType = async (taxType) => {
    setUserTaxType(taxType);
    try {
      const res = await fetch(apiUrl('/api/auth/me/'), {
        method: 'PATCH',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tax_type: taxType }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        console.error('Failed to persist tax type:', err || res.status);
      }
    } catch (err) {
      console.error('Failed to persist tax type:', err);
    }
  };

  const updateUserTaxRate = async (rate) => {
    const validation = validationService.validateTaxRate(rate, userCountry);
    if (!validation.isValid) {
      console.error('Tax rate validation failed:', validation.errors);
      return false;
    }

    const rounded = calculationEngine.round(parseFloat(rate));
    setUserTaxRate(rounded);

    try {
      const res = await fetch(apiUrl('/api/auth/me/'), {
        method: 'PATCH',
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tax_rate: rounded }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        console.error('Failed to persist tax rate:', err || res.status);
        return false;
      }
    } catch (err) {
      console.error('Failed to persist tax rate:', err);
      return false;
    }

    return true;
  };

  // Combine all transactions for AI analysis
  const transactions = [...filteredExpenses, ...income];

  const refreshBankFeedExpenses = useCallback(async () => {
    try {
      const response = await bankingTransactionsAPI.getAll();
      const items = Array.isArray(response.data) ? response.data : response.data.results || [];
      setBankFeedExpenses(items.filter((item) => parseFloat(item.amount || 0) < 0).map(mapBankTransactionToExpense));
    } catch (err) {
      console.error('Failed to refresh bank feed expenses:', err);
    }
  }, [mapBankTransactionToExpense]);

  const value = {
    // Data
    expenses: filteredExpenses,
    allExpenses: mergedExpenses,
    manualExpenses: expenses,
    bankFeedExpenses,
    income,
    budgets,
    transactions,
    portfolioData,
    expenseSourceFilter,
    setExpenseSourceFilter,
    expenseSourceOptions: EXPENSE_SOURCE_OPTIONS,

    // Financial Modeling Data
    models,
    currentModel,
    modelTemplates,
    scenarios,
    sensitivityAnalyses,
    aiInsights,
    customKPIs,
    reports,
    consolidations,
    taxCalculations,
    complianceDeadlines,
    cashflowForecasts,

    // Financial Modeling setters (exposed for screens that manage these)
    setModels,
    setCurrentModel,
    setModelTemplates,
    setScenarios,
    setSensitivityAnalyses,
    setAiInsights,
    setCustomKPIs,
    setReports,
    setConsolidations,
    setTaxCalculations,
    setComplianceDeadlines,
    setCashflowForecasts,

    // Enterprise Data
    organizations,
    entities,
    teamMembers,
    roles,
    permissions,
    auditLogs,
    taxExposures,

    // Enterprise setters (exposed for admin screens)
    setOrganizations,
    setEntities,
    setTeamMembers,
    setRoles,
    setPermissions,
    setAuditLogs,
    setTaxExposures,

    // Loading and Error States
    loading,
    error,

    // CRUD Operations
    addExpense,
    deleteExpense,
    updateExpense,
    addIncome,
    deleteIncome,
    updateIncome,
    addBudget,
    updateBudget,
    deleteBudget,

    // Financial Modeling Operations
    loadModelTemplates,
    loadFinancialModels,
    createFinancialModel,
    calculateFinancialModel,
    loadScenarios,
    loadAIInsights,
    loadReports,

    // Enterprise Operations
    loadOrganizations,
    loadEntities,

    // Calculated Values (from engine)
    totalIncome,
    totalExpenses,
    balance,
    netIncome,
    taxAmount,

    // Financial Summary (comprehensive)
    financialSummary,
    validationResults,

    // Monthly Tracking
    monthlySummary,
    selectedMonth,
    availableMonths,
    changeMonth,
    monthlyAnalysisService,

    // Tax & Country Settings
    userCountry,
    userTaxRate,
    userTaxType,
    updateUserCountry,
    updateUserTaxType,
    updateUserTaxRate,

    // Calculation Engine (expose for components that need it)
    calculationEngine,
    validationService,

    // Manual recalculation trigger
    recalculateAll,
    refreshBankFeedExpenses
  };

  return (
    <FinanceContext.Provider value={value}>
      {children}
    </FinanceContext.Provider>
  );
};

export const useFinance = () => {
  const context = useContext(FinanceContext);
  if (!context) {
    throw new Error('useFinance must be used within a FinanceProvider');
  }
  return context;
};
