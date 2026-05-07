/**
 * Ledgora - AI-Powered Validation Service
 *
 * Provides intelligent validation, anomaly detection, and warnings
 * to prevent user errors and maintain data integrity.
 */

import calculationEngine from './calculationEngine';

// ==================== VALIDATION RULES ====================

const VALIDATION_RULES = {
  TAX_RATE: {
    min: 0,
    max: 100,
    warningThreshold: 60,
    errorThreshold: 100
  },
  INCOME: {
    min: 0,
    max: 100000000, // 100 million
    warningThreshold: 10000000 // 10 million
  },
  EXPENSE: {
    min: 0,
    max: 100000000,
    warningThreshold: 1000000
  },
  BUDGET: {
    min: 0,
    max: 100000000
  },
  EXPENSE_TO_INCOME_RATIO: {
    warning: 0.8, // 80%
    critical: 1.5  // 150%
  },
  SAVINGS_RATE: {
    healthy: 20, // 20% or more
    warning: 10,  // Below 10%
    critical: 0   // No savings
  }
};

const normalizeSourceType = (sourceType) => {
  if (sourceType === 'bank_feed' || sourceType === 'imported') {
    return 'imported';
  }
  return 'manual';
};

const getSourceLabel = (sourceType) => {
  if (normalizeSourceType(sourceType) === 'imported') {
    return 'Imported bank feed';
  }
  return 'Manual entries';
};

const formatCurrency = (value) => `$${calculationEngine.round(parseFloat(value || 0)).toFixed(2)}`;

const isInMonth = (date, year, month) => {
  const current = new Date(date);
  return current.getFullYear() === year && current.getMonth() === month;
};

const getExpenseSourceBreakdown = (expenses = []) => {
  return expenses.reduce((accumulator, expense) => {
    const source = normalizeSourceType(expense.sourceType);
    if (!accumulator[source]) {
      accumulator[source] = {
        source,
        label: getSourceLabel(source),
        amount: 0,
        count: 0,
      };
    }

    accumulator[source].amount = calculationEngine.round(
      accumulator[source].amount + parseFloat(expense.amount || 0)
    );
    accumulator[source].count += 1;
    return accumulator;
  }, {
    manual: { source: 'manual', label: getSourceLabel('manual'), amount: 0, count: 0 },
    imported: { source: 'imported', label: getSourceLabel('imported'), amount: 0, count: 0 },
  });
};

const getDominantSource = (sourceBreakdown = {}) => {
  return Object.values(sourceBreakdown)
    .sort((left, right) => right.amount - left.amount)
    .find((entry) => entry.amount > 0) || null;
};

const getAverageSourceAmounts = (historicalData = []) => {
  if (!historicalData.length) {
    return {
      manual: 0,
      imported: 0,
    };
  }

  return historicalData.reduce((accumulator, entry) => {
    const breakdown = entry.sourceBreakdown || {};
    accumulator.manual += parseFloat(breakdown.manual?.amount || 0);
    accumulator.imported += parseFloat(breakdown.imported?.amount || 0);
    return accumulator;
  }, {
    manual: 0,
    imported: 0,
  });
};

const buildBudgetAlertDetails = (budgets = [], expenses = [], selectedMonth = null) => {
  const scopedExpenses = selectedMonth
    ? expenses.filter((expense) => expense.date && isInMonth(expense.date, selectedMonth.year, selectedMonth.month))
    : expenses;

  return budgets.reduce((alerts, budget) => {
    const budgetLimit = parseFloat(budget.limit || budget.amount || 0);
    const categoryExpenses = scopedExpenses.filter((expense) => expense.category === budget.category);
    const spent = calculationEngine.calculateTotalExpenses(categoryExpenses);

    if (!budgetLimit || !spent) {
      return alerts;
    }

    const utilization = calculationEngine.calculateBudgetUtilization(budgetLimit, spent);
    if (!utilization.isOverBudget && utilization.percentageUsed < 90) {
      return alerts;
    }

    const sourceBreakdown = getExpenseSourceBreakdown(categoryExpenses);
    const dominantSource = getDominantSource(sourceBreakdown);
    const driverText = dominantSource
      ? `${dominantSource.label} account for ${formatCurrency(dominantSource.amount)} of this category.`
      : 'No dominant source detected.';
    const message = utilization.isOverBudget
      ? `${budget.category} is over budget by ${formatCurrency(Math.abs(utilization.remaining))}. ${driverText}`
      : `${budget.category} has used ${utilization.percentageUsed.toFixed(0)}% of budget. ${driverText}`;

    alerts.push({
      category: budget.category,
      severity: utilization.isOverBudget ? 'warning' : 'info',
      spent,
      budget: budgetLimit,
      remaining: utilization.remaining,
      percentageUsed: utilization.percentageUsed,
      dominantSource,
      sourceBreakdown,
      message,
    });

    return alerts;
  }, []);
};

// ==================== TAX VALIDATION ====================

/**
 * Validate tax rate
 */
export const validateTaxRate = (taxRate, country = null) => {
  const errors = [];
  const warnings = [];
  const rate = parseFloat(taxRate || 0);

  // Range validation
  if (rate < VALIDATION_RULES.TAX_RATE.min) {
    errors.push('Tax rate cannot be negative');
  }
  if (rate >VALIDATION_RULES.TAX_RATE.max) {
    errors.push('Tax rate cannot exceed 100%');
  }

  // Warning for high rates
  if (rate >VALIDATION_RULES.TAX_RATE.warningThreshold && rate <= VALIDATION_RULES.TAX_RATE.max) {
    warnings.push(`Tax rate of ${rate}% is very high. Please verify this is correct for ${country || 'your country'}.`);
  }

  // AI suggestion for unusual rates
  if (rate === 0 && country) {
    warnings.push('0% tax rate detected. This is only valid for tax havens like Cayman Islands or Bahamas.');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    confidence: rate >= 5 && rate <= 50 ? 95 : 70
  };
};

/**
 * Validate tax calculation
 */
export const validateTaxCalculation = (amount, taxRate, calculatedTax) => {
  const expectedTax = calculationEngine.calculateTax(amount, taxRate);
  const difference = Math.abs(expectedTax - calculatedTax);

  if (difference > 0.01) {
    return {
      isValid: false,
      error: 'Tax calculation mismatch detected',
      expected: expectedTax,
      actual: calculatedTax,
      difference
    };
  }

  return {
    isValid: true
  };
};

// ==================== INCOME VALIDATION ====================

/**
 * Validate income entry
 */
export const validateIncome = (amount, category = null) => {
  const errors = [];
  const warnings = [];
  const value = parseFloat(amount || 0);

  // Range validation
  if (value < VALIDATION_RULES.INCOME.min) {
    errors.push('Income cannot be negative');
  }
  if (value >VALIDATION_RULES.INCOME.max) {
    errors.push(`Income amount exceeds maximum allowed (${VALIDATION_RULES.INCOME.max.toLocaleString()})`);
  }

  // Warning for unusually high values
  if (value >VALIDATION_RULES.INCOME.warningThreshold) {
    warnings.push(`Income of ${value.toLocaleString()} is unusually high. Please verify this amount.`);
  }

  // Category-specific validation
  if (category === 'salary' && value > 10000000) {
    warnings.push('Salary exceeds 10 million. Please ensure this is correct.');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

// ==================== EXPENSE VALIDATION ====================

/**
 * Validate expense entry
 */
export const validateExpense = (amount, category = null, budget = null) => {
  const errors = [];
  const warnings = [];
  const value = parseFloat(amount || 0);

  // Range validation
  if (value < VALIDATION_RULES.EXPENSE.min) {
    errors.push('Expense cannot be negative');
  }
  if (value >VALIDATION_RULES.EXPENSE.max) {
    errors.push(`Expense amount exceeds maximum allowed (${VALIDATION_RULES.EXPENSE.max.toLocaleString()})`);
  }

  // Warning for unusually high values
  if (value >VALIDATION_RULES.EXPENSE.warningThreshold) {
    warnings.push(`Expense of ${value.toLocaleString()} is unusually high. Please verify this amount.`);
  }

  // Budget check
  if (budget && value > budget) {
    warnings.push(`This expense exceeds the ${category} budget by ${(value - budget).toLocaleString()}`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Validate expense against income
 */
export const validateExpenseRatio = (totalExpenses, totalIncome) => {
  const errors = [];
  const warnings = [];

  const ratio = totalIncome > 0 ? totalExpenses / totalIncome : 0;

  if (ratio >VALIDATION_RULES.EXPENSE_TO_INCOME_RATIO.critical) {
    errors.push(`Expenses exceed income by ${((ratio - 1) * 100).toFixed(1)}%. This is financially unsustainable.`);
  } else if (ratio >VALIDATION_RULES.EXPENSE_TO_INCOME_RATIO.warning) {
    warnings.push(`Expenses are ${(ratio * 100).toFixed(1)}% of income. Consider reducing spending.`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    ratio: calculationEngine.round(ratio * 100)
  };
};

// ==================== BUDGET VALIDATION ====================

/**
 * Validate budget allocation
 */
export const validateBudget = (amount, category = null) => {
  const errors = [];
  const warnings = [];
  const value = parseFloat(amount || 0);

  // Range validation
  if (value < VALIDATION_RULES.BUDGET.min) {
    errors.push('Budget cannot be negative');
  }
  if (value >VALIDATION_RULES.BUDGET.max) {
    errors.push(`Budget amount exceeds maximum allowed (${VALIDATION_RULES.BUDGET.max.toLocaleString()})`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Validate budget vs income
 */
export const validateBudgetVsIncome = (totalBudget, totalIncome) => {
  const errors = [];
  const warnings = [];

  if (totalBudget > totalIncome) {
    warnings.push(`Total budget (${totalBudget.toLocaleString()}) exceeds income (${totalIncome.toLocaleString()}). You may need to reduce spending plans.`);
  }

  const budgetRatio = totalIncome > 0 ? (totalBudget / totalIncome) * 100 : 0;

  if (budgetRatio > 90) {
    warnings.push(`Budget allocates ${budgetRatio.toFixed(1)}% of income. Consider leaving buffer for savings.`);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    ratio: calculationEngine.round(budgetRatio)
  };
};

// ==================== FINANCIAL HEALTH VALIDATION ====================

/**
 * Validate overall financial health
 */
export const validateFinancialHealth = (summary) => {
  const errors = [];
  const warnings = [];
  const recommendations = [];

  // Negative balance check
  if (summary.balance.net < 0) {
    errors.push('Negative balance detected. Expenses exceed income.');
    recommendations.push('Reduce expenses or increase income sources');
  }

  // Savings rate check
  const savingsRate = summary.balance.savingsRate;
  if (savingsRate < VALIDATION_RULES.SAVINGS_RATE.critical) {
    errors.push('No savings detected. All income is being spent.');
    recommendations.push('Aim to save at least 10-20% of income');
  } else if (savingsRate < VALIDATION_RULES.SAVINGS_RATE.warning) {
    warnings.push(`Savings rate is only ${savingsRate.toFixed(1)}%. Financial experts recommend at least 20%.`);
    recommendations.push('Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings');
  }

  // Budget utilization check
  const overBudgetCategories = summary.budget.utilization.filter(cat => cat.isOverBudget);
  if (overBudgetCategories.length > 0) {
    warnings.push(`${overBudgetCategories.length} categories are over budget`);
    overBudgetCategories.forEach(cat => {
      recommendations.push(`Reduce ${cat.category} spending by ${Math.abs(cat.remaining).toLocaleString()}`);
    });
  }

  // Tax efficiency check
  if (summary.tax.effectiveRate > 40) {
    warnings.push(`Effective tax rate is ${summary.tax.effectiveRate.toFixed(1)}%. Consider tax optimization strategies.`);
    recommendations.push('Consult a tax professional about legal deductions and credits');
  }

  // Runway check
  const runway = summary.balance.runway;
  if (runway !== 'Infinite' && runway < 6) {
    warnings.push(`Financial runway is only ${runway.toFixed(1)} months. Build emergency fund.`);
    recommendations.push('Aim for 6-12 months of expenses in emergency savings');
  }

  // Generate health score (0-100)
  let healthScore = 100;
  healthScore -= errors.length * 20;
  healthScore -= warnings.length * 10;
  healthScore = Math.max(0, healthScore);

  return {
    isHealthy: errors.length === 0 && warnings.length <= 2,
    healthScore,
    errors,
    warnings,
    recommendations,
    status: healthScore >= 80 ? 'Excellent' :
            healthScore >= 60 ? 'Good' :
            healthScore >= 40 ? 'Fair' :
            'Poor'
  };
};

// ==================== ANOMALY DETECTION ====================

/**
 * Detect unusual patterns in financial data
 */
export const detectAnomalies = (currentData, historicalData = []) => {
  const anomalies = [];

  if (historicalData.length === 0) {
    return { hasAnomalies: false, anomalies };
  }

  // Calculate historical averages
  const avgIncome = historicalData.reduce((sum, d) => sum + d.income, 0) / historicalData.length;
  const avgExpenses = historicalData.reduce((sum, d) => sum + d.expenses, 0) / historicalData.length;
  const averageSourceTotals = getAverageSourceAmounts(historicalData);
  const averageSourceBreakdown = {
    manual: averageSourceTotals.manual / historicalData.length,
    imported: averageSourceTotals.imported / historicalData.length,
  };

  // Check for sudden spikes
  if (avgIncome > 0 && currentData.income > avgIncome * 2) {
    anomalies.push({
      type: 'spike',
      field: 'income',
      message: `Income is ${((currentData.income / avgIncome - 1) * 100).toFixed(0)}% higher than average`,
      severity: 'info'
    });
  }

  if (avgExpenses > 0 && currentData.expenses > avgExpenses * 2) {
    const dominantSource = getDominantSource(currentData.expenseSourceBreakdown);
    const sourceDelta = dominantSource
      ? dominantSource.amount - (averageSourceBreakdown[dominantSource.source] || 0)
      : 0;
    anomalies.push({
      type: 'spike',
      field: 'expenses',
      message: `Expenses are ${((currentData.expenses / avgExpenses - 1) * 100).toFixed(0)}% higher than average${dominantSource ? `, driven mostly by ${dominantSource.label.toLowerCase()} (${formatCurrency(sourceDelta)} above their average).` : ''}`,
      severity: 'warning',
      dominantSource,
    });
  }

  // Check for sudden drops
  if (avgIncome > 0 && currentData.income < avgIncome * 0.5) {
    anomalies.push({
      type: 'drop',
      field: 'income',
      message: `Income dropped by ${((1 - currentData.income / avgIncome) * 100).toFixed(0)}%`,
      severity: 'warning'
    });
  }

  return {
    hasAnomalies: anomalies.length > 0,
    anomalies
  };
};

// ==================== COMPREHENSIVE VALIDATION ====================

/**
 * Validate all financial data comprehensively
 * This is the master validation function
 */
export const validateAllFinancialData = (data) => {
  const results = {
    isValid: true,
    errors: [],
    warnings: [],
    recommendations: [],
    validations: {},
    warningDetails: [],
    anomalies: [],
    sourceInsights: {
      budgetAlerts: [],
      anomalies: [],
    }
  };

  // Tax validation
  if (data.taxRate !== undefined) {
    const taxValidation = validateTaxRate(data.taxRate, data.country);
    results.validations.tax = taxValidation;
    results.errors.push(...taxValidation.errors);
    results.warnings.push(...taxValidation.warnings);
    if (!taxValidation.isValid) results.isValid = false;
  }

  // Income validation
  if (data.totalIncome !== undefined) {
    const incomeValidation = validateIncome(data.totalIncome);
    results.validations.income = incomeValidation;
    results.errors.push(...incomeValidation.errors);
    results.warnings.push(...incomeValidation.warnings);
    if (!incomeValidation.isValid) results.isValid = false;
  }

  // Expense validation
  if (data.totalExpenses !== undefined) {
    const expenseValidation = validateExpense(data.totalExpenses);
    results.validations.expenses = expenseValidation;
    results.errors.push(...expenseValidation.errors);
    results.warnings.push(...expenseValidation.warnings);
    if (!expenseValidation.isValid) results.isValid = false;

    // Expense ratio validation
    if (data.totalIncome !== undefined) {
      const ratioValidation = validateExpenseRatio(data.totalExpenses, data.totalIncome);
      results.validations.expenseRatio = ratioValidation;
      results.errors.push(...ratioValidation.errors);
      results.warnings.push(...ratioValidation.warnings);
      if (!ratioValidation.isValid) results.isValid = false;
    }
  }

  // Budget validation
  if (data.totalBudget !== undefined) {
    const budgetValidation = validateBudget(data.totalBudget);
    results.validations.budget = budgetValidation;
    results.errors.push(...budgetValidation.errors);
    results.warnings.push(...budgetValidation.warnings);
    if (!budgetValidation.isValid) results.isValid = false;

    // Budget vs income validation
    if (data.totalIncome !== undefined) {
      const budgetIncomeValidation = validateBudgetVsIncome(data.totalBudget, data.totalIncome);
      results.validations.budgetVsIncome = budgetIncomeValidation;
      results.errors.push(...budgetIncomeValidation.errors);
      results.warnings.push(...budgetIncomeValidation.warnings);
    }
  }

  // Financial health validation
  if (data.summary) {
    const healthValidation = validateFinancialHealth(data.summary);
    results.validations.health = healthValidation;
    results.errors.push(...healthValidation.errors);
    results.warnings.push(...healthValidation.warnings);
    results.recommendations.push(...healthValidation.recommendations);
    results.healthScore = healthValidation.healthScore;
    results.healthStatus = healthValidation.status;
  }

  if (Array.isArray(data.budgets) && Array.isArray(data.expenseTransactions)) {
    const budgetAlerts = buildBudgetAlertDetails(data.budgets, data.expenseTransactions, data.selectedMonth);
    results.warningDetails = budgetAlerts;
    results.sourceInsights.budgetAlerts = budgetAlerts;
    results.warnings.push(...budgetAlerts.slice(0, 3).map((alert) => alert.message));
  }

  if (data.selectedMonth && Array.isArray(data.expenseTransactions)) {
    const currentMonthExpenses = data.expenseTransactions.filter(
      (expense) => expense.date && isInMonth(expense.date, data.selectedMonth.year, data.selectedMonth.month)
    );
    const anomalyResult = detectAnomalies({
      income: parseFloat(data.monthlyIncome || 0),
      expenses: calculationEngine.calculateTotalExpenses(currentMonthExpenses),
      expenseSourceBreakdown: getExpenseSourceBreakdown(currentMonthExpenses),
    }, Array.isArray(data.historicalExpenseData) ? data.historicalExpenseData : []);

    results.anomalies = anomalyResult.anomalies;
    results.sourceInsights.anomalies = anomalyResult.anomalies;
  }

  return results;
};

// ==================== EXPORT ====================

const validationService = {
  validateTaxRate,
  validateTaxCalculation,
  validateIncome,
  validateExpense,
  validateExpenseRatio,
  validateBudget,
  validateBudgetVsIncome,
  validateFinancialHealth,
  detectAnomalies,
  validateAllFinancialData
};

export default validationService;
