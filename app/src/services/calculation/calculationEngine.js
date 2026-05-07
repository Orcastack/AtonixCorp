/**
 * Ledgora - Unified Financial Calculation Engine
 *
 * This is the SINGLE SOURCE OF TRUTH for all financial calculations.
 * Every module must use these functions - NO calculations in components.
 *
 * Purpose:
 * - Eliminate duplicate logic
 * - Prevent calculation drift
 * - Ensure consistent rounding
 * - Maintain synchronized totals
 * - Enable real-time updates
 */

// ==================== CONFIGURATION ====================

const PRECISION = 2; // All financial values rounded to 2 decimals
const PERCENTAGE_DIVISOR = 100;

// ==================== CORE MATH UTILITIES ====================

/**
 * Round to specified decimal places (default: 2)
 * Ensures consistent rounding across entire platform
 */
export const round = (value, decimals = PRECISION) => {
  const multiplier = Math.pow(10, decimals);
  return Math.round(value * multiplier) / multiplier;
};

/**
 * Safe addition - prevents floating point errors
 */
export const add = (...values) => {
  const sum = values.reduce((acc, val) => acc + parseFloat(val || 0), 0);
  return round(sum);
};

/**
 * Safe subtraction
 */
export const subtract = (minuend, ...subtrahends) => {
  const total = subtrahends.reduce((acc, val) => acc - parseFloat(val || 0), parseFloat(minuend || 0));
  return round(total);
};

/**
 * Safe multiplication
 */
export const multiply = (...values) => {
  const product = values.reduce((acc, val) => acc * parseFloat(val || 0), 1);
  return round(product);
};

/**
 * Safe division (prevents divide by zero)
 */
export const divide = (dividend, divisor) => {
  if (divisor === 0 || divisor === null || divisor === undefined) {
    return 0;
  }
  return round(parseFloat(dividend || 0) / parseFloat(divisor));
};

// ==================== PERCENTAGE CALCULATIONS ====================

/**
 * Calculate percentage of a value
 * Example: percentage(10000, 15) = 1500
 */
export const percentage = (amount, rate) => {
  return round((parseFloat(amount || 0) * parseFloat(rate || 0)) / PERCENTAGE_DIVISOR);
};

/**
 * Calculate percentage change between two values
 * Example: percentageChange(100, 150) = 50
 */
export const percentageChange = (oldValue, newValue) => {
  if (oldValue === 0 || oldValue === null || oldValue === undefined) {
    return newValue > 0 ? 100 : 0;
  }
  return round(((parseFloat(newValue || 0) - parseFloat(oldValue || 0)) / parseFloat(oldValue)) * 100);
};

/**
 * Calculate what percentage one value is of another
 * Example: percentageOf(25, 100) = 25
 */
export const percentageOf = (part, whole) => {
  if (whole === 0 || whole === null || whole === undefined) {
    return 0;
  }
  return round((parseFloat(part || 0) / parseFloat(whole)) * 100);
};

// ==================== TAX CALCULATIONS ====================

/**
 * Calculate tax amount
 * Formula: amount × (taxRate / 100)
 */
export const calculateTax = (amount, taxRate) => {
  return percentage(amount, taxRate);
};

/**
 * Calculate amount after tax deduction
 * For income: income - tax
 */
export const calculateNetAfterTax = (amount, taxRate) => {
  const tax = calculateTax(amount, taxRate);
  return subtract(amount, tax);
};

/**
 * Calculate amount with tax added
 * For VAT: amount + tax
 */
export const calculateTotalWithTax = (amount, taxRate) => {
  const tax = calculateTax(amount, taxRate);
  return add(amount, tax);
};

/**
 * Calculate effective tax rate (actual tax paid as %)
 */
export const calculateEffectiveTaxRate = (grossAmount, taxPaid) => {
  return percentageOf(taxPaid, grossAmount);
};

// ==================== INCOME CALCULATIONS ====================

/**
 * Calculate total income from multiple sources
 */
export const calculateTotalIncome = (incomes = []) => {
  const total = incomes.reduce((sum, income) => {
    return sum + parseFloat(income.amount || 0);
  }, 0);
  return round(total);
};

/**
 * Calculate monthly income average
 */
export const calculateMonthlyIncome = (incomes = []) => {
  const total = calculateTotalIncome(incomes);
  const months = 12;
  return divide(total, months);
};

/**
 * Calculate income after tax
 */
export const calculateNetIncome = (grossIncome, taxRate) => {
  return calculateNetAfterTax(grossIncome, taxRate);
};

/**
 * Calculate income breakdown by category
 */
export const calculateIncomeBreakdown = (incomes = []) => {
  const breakdown = {};
  let total = 0;

  incomes.forEach(income => {
    const category = income.category || 'Other';
    const amount = parseFloat(income.amount || 0);

    if (!breakdown[category]) {
      breakdown[category] = 0;
    }
    breakdown[category] = round(breakdown[category] + amount);
    total = round(total + amount);
  });

  // Calculate percentages
  Object.keys(breakdown).forEach(category => {
    breakdown[category] = {
      amount: breakdown[category],
      percentage: percentageOf(breakdown[category], total)
    };
  });

  return { breakdown, total };
};

// ==================== EXPENSE CALCULATIONS ====================

/**
 * Calculate total expenses
 */
export const calculateTotalExpenses = (expenses = []) => {
  const total = expenses.reduce((sum, expense) => {
    return sum + parseFloat(expense.amount || 0);
  }, 0);
  return round(total);
};

/**
 * Calculate expenses by category
 */
export const calculateExpensesByCategory = (expenses = []) => {
  const categories = {};
  let total = 0;

  expenses.forEach(expense => {
    const category = expense.category || 'Other';
    const amount = parseFloat(expense.amount || 0);

    if (!categories[category]) {
      categories[category] = 0;
    }
    categories[category] = round(categories[category] + amount);
    total = round(total + amount);
  });

  // Calculate percentages
  Object.keys(categories).forEach(category => {
    categories[category] = {
      amount: categories[category],
      percentage: percentageOf(categories[category], total)
    };
  });

  return { categories, total };
};

/**
 * Calculate monthly expense average
 */
export const calculateMonthlyExpenses = (expenses = []) => {
  const total = calculateTotalExpenses(expenses);
  const months = 12;
  return divide(total, months);
};

// ==================== BUDGET CALCULATIONS ====================

/**
 * Calculate total budget allocation
 */
export const calculateTotalBudget = (budgets = []) => {
  const total = budgets.reduce((sum, budget) => {
    return sum + parseFloat(budget.amount || 0);
  }, 0);
  return round(total);
};

/**
 * Calculate budget utilization
 * Returns: { budgeted, spent, remaining, percentageUsed }
 */
export const calculateBudgetUtilization = (budgetAmount, spent) => {
  const budgeted = parseFloat(budgetAmount || 0);
  const spentAmount = parseFloat(spent || 0);
  const remaining = subtract(budgeted, spentAmount);
  const percentageUsed = percentageOf(spentAmount, budgeted);

  return {
    budgeted: round(budgeted),
    spent: round(spentAmount),
    remaining: round(remaining),
    percentageUsed: round(percentageUsed),
    isOverBudget: remaining < 0
  };
};

/**
 * Calculate budget vs expenses for all categories
 */
export const calculateBudgetVsExpenses = (budgets = [], expenses = []) => {
  const expensesByCategory = {};

  // Sum expenses by category
  expenses.forEach(expense => {
    const category = expense.category || 'Other';
    const amount = parseFloat(expense.amount || 0);
    expensesByCategory[category] = (expensesByCategory[category] || 0) + amount;
  });

  // Compare with budgets
  const comparison = budgets.map(budget => {
    const spent = expensesByCategory[budget.category] || 0;
    return {
      category: budget.category,
      ...calculateBudgetUtilization(budget.amount, spent)
    };
  });

  return comparison;
};

// ==================== BALANCE CALCULATIONS ====================

/**
 * Calculate net balance (income - expenses)
 */
export const calculateNetBalance = (totalIncome, totalExpenses) => {
  return subtract(totalIncome, totalExpenses);
};

/**
 * Calculate savings rate
 */
export const calculateSavingsRate = (totalIncome, totalExpenses) => {
  const savings = calculateNetBalance(totalIncome, totalExpenses);
  return percentageOf(savings, totalIncome);
};

/**
 * Calculate burn rate (monthly spending)
 */
export const calculateBurnRate = (expenses = [], months = 1) => {
  const total = calculateTotalExpenses(expenses);
  return divide(total, months);
};

/**
 * Calculate runway (how long savings will last)
 */
export const calculateRunway = (savings, monthlyBurn) => {
  if (monthlyBurn === 0) return Infinity;
  return divide(savings, monthlyBurn);
};

// ==================== SUMMARY CALCULATIONS ====================

/**
 * Calculate complete financial summary
 * This is the master function that synchronizes everything
 */
export const calculateFinancialSummary = ({
  incomes = [],
  expenses = [],
  budgets = [],
  taxRate = 0,
  country = null
}) => {
  // Income calculations
  const grossIncome = calculateTotalIncome(incomes);
  const incomeTax = calculateTax(grossIncome, taxRate);
  const netIncome = calculateNetAfterTax(grossIncome, taxRate);
  const monthlyIncome = divide(netIncome, 12);

  // Expense calculations
  const totalExpenses = calculateTotalExpenses(expenses);
  const monthlyExpenses = divide(totalExpenses, 12);
  const expensesByCategory = calculateExpensesByCategory(expenses);

  // Budget calculations
  const totalBudget = calculateTotalBudget(budgets);
  const budgetUtilization = calculateBudgetVsExpenses(budgets, expenses);

  // Balance calculations
  const netBalance = calculateNetBalance(netIncome, totalExpenses);
  const savingsRate = calculateSavingsRate(netIncome, totalExpenses);
  const burnRate = monthlyExpenses;
  const runway = calculateRunway(netBalance, burnRate);

  // Income breakdown
  const incomeBreakdown = calculateIncomeBreakdown(incomes);

  return {
    // Income
    income: {
      gross: round(grossIncome),
      tax: round(incomeTax),
      net: round(netIncome),
      monthly: round(monthlyIncome),
      breakdown: incomeBreakdown.breakdown
    },
    // Expenses
    expenses: {
      total: round(totalExpenses),
      monthly: round(monthlyExpenses),
      byCategory: expensesByCategory.categories
    },
    // Budget
    budget: {
      total: round(totalBudget),
      utilization: budgetUtilization
    },
    // Balance & Metrics
    balance: {
      net: round(netBalance),
      savingsRate: round(savingsRate),
      burnRate: round(burnRate),
      runway: runway === Infinity ? 'Infinite' : round(runway)
    },
    // Tax Info
    tax: {
      rate: taxRate,
      amount: round(incomeTax),
      country: country,
      effectiveRate: calculateEffectiveTaxRate(grossIncome, incomeTax)
    },
    // Status
    status: {
      isPositive: netBalance > 0,
      isOverBudget: totalExpenses > totalBudget,
      needsAttention: netBalance < 0 || totalExpenses > totalBudget
    }
  };
};

// ==================== VALIDATION ====================

/**
 * Validate financial data for errors
 */
export const validateFinancialData = (data) => {
  const errors = [];
  const warnings = [];

  // Check for negative values
  if (data.income < 0) errors.push('Income cannot be negative');
  if (data.expenses < 0) errors.push('Expenses cannot be negative');
  if (data.budget < 0) errors.push('Budget cannot be negative');

  // Check for unrealistic tax rates
  if (data.taxRate < 0 || data.taxRate > 100) {
    errors.push('Tax rate must be between 0% and 100%');
  }
  if (data.taxRate > 60) {
    warnings.push('Tax rate exceeds 60% - please verify this is correct');
  }

  // Check for suspicious patterns
  if (data.expenses > data.income * 2) {
    warnings.push('Expenses exceed income by more than 200% - please review');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

// ==================== EXPORT ALL ====================

const calculationEngine = {
  // Core math
  round,
  add,
  subtract,
  multiply,
  divide,

  // Percentages
  percentage,
  percentageChange,
  percentageOf,

  // Tax
  calculateTax,
  calculateNetAfterTax,
  calculateTotalWithTax,
  calculateEffectiveTaxRate,

  // Income
  calculateTotalIncome,
  calculateMonthlyIncome,
  calculateNetIncome,
  calculateIncomeBreakdown,

  // Expenses
  calculateTotalExpenses,
  calculateExpensesByCategory,
  calculateMonthlyExpenses,

  // Budget
  calculateTotalBudget,
  calculateBudgetUtilization,
  calculateBudgetVsExpenses,

  // Balance
  calculateNetBalance,
  calculateSavingsRate,
  calculateBurnRate,
  calculateRunway,

  // Summary
  calculateFinancialSummary,

  // Validation
  validateFinancialData
};

export default calculationEngine;
