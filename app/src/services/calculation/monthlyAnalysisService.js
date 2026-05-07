/**
 * Ledgora - Monthly Financial Tracking & Analysis Service
 *
 * Provides automatic monthly aggregation, analysis, and insights
 * Integrates with the unified calculation engine
 */

import calculationEngine from './calculationEngine';

// ==================== DATE UTILITIES ====================

/**
 * Get start and end dates for a given month
 */
export const getMonthBounds = (year, month) => {
  const startDate = new Date(year, month, 1);
  const endDate = new Date(year, month + 1, 0, 23, 59, 59, 999);
  return { startDate, endDate };
};

/**
 * Get current month and year
 */
export const getCurrentMonth = () => {
  const now = new Date();
  return {
    year: now.getFullYear(),
    month: now.getMonth(), // 0-indexed
    monthName: now.toLocaleString('default', { month: 'long' }),
    yearMonth: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  };
};

/**
 * Format date to YYYY-MM for grouping
 */
export const formatYearMonth = (date) => {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

/**
 * Check if date is in specified month
 */
export const isInMonth = (date, year, month) => {
  const d = new Date(date);
  return d.getFullYear() === year && d.getMonth() === month;
};

/**
 * Get all unique months from transaction dates
 */
export const getAvailableMonths = (transactions) => {
  const monthsSet = new Set();

  transactions.forEach(transaction => {
    if (transaction.date) {
      monthsSet.add(formatYearMonth(transaction.date));
    }
  });

  return Array.from(monthsSet).sort().reverse();
};

// ==================== FILTERING ====================

/**
 * Filter transactions by month
 */
export const filterByMonth = (transactions, year, month) => {
  return transactions.filter(transaction => {
    if (!transaction.date) return false;
    return isInMonth(transaction.date, year, month);
  });
};

/**
 * Filter by type and month
 */
export const filterByTypeAndMonth = (transactions, type, year, month) => {
  return transactions.filter(transaction => {
    if (transaction.type !== type) return false;
    if (!transaction.date) return false;
    return isInMonth(transaction.date, year, month);
  });
};

/**
 * Get transactions for specific date range
 */
export const filterByDateRange = (transactions, startDate, endDate) => {
  const start = new Date(startDate);
  const end = new Date(endDate);

  return transactions.filter(transaction => {
    if (!transaction.date) return false;
    const transactionDate = new Date(transaction.date);
    return transactionDate >= start && transactionDate <= end;
  });
};

// ==================== MONTHLY AGGREGATION ====================

/**
 * Calculate monthly income total
 */
export const calculateMonthlyIncome = (incomes, year, month) => {
  const monthlyIncomes = filterByMonth(incomes, year, month);
  return {
    transactions: monthlyIncomes,
    total: calculationEngine.calculateTotalIncome(monthlyIncomes.map(i => ({ amount: i.amount }))),
    count: monthlyIncomes.length
  };
};

/**
 * Calculate monthly expenses total
 */
export const calculateMonthlyExpenses = (expenses, year, month) => {
  const monthlyExpenses = filterByMonth(expenses, year, month);
  return {
    transactions: monthlyExpenses,
    total: calculationEngine.calculateTotalExpenses(monthlyExpenses),
    count: monthlyExpenses.length
  };
};

/**
 * Calculate monthly tax
 */
export const calculateMonthlyTax = (incomes, year, month, taxRate) => {
  const monthlyIncome = calculateMonthlyIncome(incomes, year, month);
  return calculationEngine.calculateTax(monthlyIncome.total, taxRate);
};

const normalizeSourceType = (sourceType) => {
  if (sourceType === 'bank_feed' || sourceType === 'imported') {
    return 'imported';
  }
  return 'manual';
};

const getSourceBreakdown = (transactions = []) => {
  const breakdown = {
    manual: { source: 'manual', label: 'Manual', amount: 0, count: 0 },
    imported: { source: 'imported', label: 'Imported Bank Feed', amount: 0, count: 0 },
  };

  transactions.forEach((transaction) => {
    const source = normalizeSourceType(transaction.sourceType);
    breakdown[source].amount = calculationEngine.round(
      breakdown[source].amount + parseFloat(transaction.amount || 0)
    );
    breakdown[source].count += 1;
  });

  return Object.values(breakdown);
};

const getSourceCategoryBreakdown = (transactions = []) => {
  const categories = {};

  transactions.forEach((transaction) => {
    const category = transaction.category || 'Other';
    const source = normalizeSourceType(transaction.sourceType);
    const amount = parseFloat(transaction.amount || 0);

    if (!categories[category]) {
      categories[category] = {
        category,
        manual: 0,
        imported: 0,
      };
    }

    categories[category][source] = calculationEngine.round(categories[category][source] + amount);
  });

  return Object.values(categories).sort(
    (left, right) => (right.manual + right.imported) - (left.manual + left.imported)
  );
};

const buildTrendComparison = (incomes, expenses, year, month) => {
  const previousMonth = month === 0 ? 11 : month - 1;
  const previousYear = month === 0 ? year - 1 : year;

  const currentIncome = calculateMonthlyIncome(incomes, year, month).total;
  const previousIncome = calculateMonthlyIncome(incomes, previousYear, previousMonth).total;
  const currentExpenses = calculateMonthlyExpenses(expenses, year, month).total;
  const previousExpenses = calculateMonthlyExpenses(expenses, previousYear, previousMonth).total;

  return {
    incomeChange: calculationEngine.percentageChange(previousIncome, currentIncome),
    expenseChange: calculationEngine.percentageChange(previousExpenses, currentExpenses),
  };
};

// ==================== CATEGORY ANALYSIS ====================

/**
 * Break down expenses by category for the month
 */
export const getCategoryBreakdown = (expenses, year, month) => {
  const monthlyExpenses = filterByMonth(expenses, year, month);
  const categories = {};
  let total = 0;

  monthlyExpenses.forEach(expense => {
    const category = expense.category || 'Other';
    const amount = parseFloat(expense.amount || 0);

    if (!categories[category]) {
      categories[category] = {
        amount: 0,
        count: 0,
        percentage: 0,
        transactions: []
      };
    }

    categories[category].amount = calculationEngine.round(categories[category].amount + amount);
    categories[category].count += 1;
    categories[category].transactions.push(expense);
    total = calculationEngine.round(total + amount);
  });

  // Calculate percentages
  Object.keys(categories).forEach(category => {
    categories[category].percentage = calculationEngine.percentageOf(categories[category].amount, total);
  });

  // Sort by amount (highest first)
  const sortedCategories = Object.entries(categories)
    .map(([name, data]) => ({ name, ...data }))
    .sort((a, b) => b.amount - a.amount);

  return {
    categories: sortedCategories,
    total,
    categoryCount: Object.keys(categories).length
  };
};

/**
 * Get top spending categories
 */
export const getTopCategories = (expenses, year, month, limit = 5) => {
  const breakdown = getCategoryBreakdown(expenses, year, month);
  return breakdown.categories.slice(0, limit);
};

// ==================== SPENDING PATTERNS ====================

/**
 * Calculate daily spending average for the month
 */
export const getDailyAverage = (expenses, year, month) => {
  const monthlyTotal = calculateMonthlyExpenses(expenses, year, month).total;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  return calculationEngine.divide(monthlyTotal, daysInMonth);
};

/**
 * Get spending by day of month
 */
export const getDailySpending = (expenses, year, month) => {
  const monthlyExpenses = filterByMonth(expenses, year, month);
  const dailyTotals = {};

  monthlyExpenses.forEach(expense => {
    const day = new Date(expense.date).getDate();
    const amount = parseFloat(expense.amount || 0);

    if (!dailyTotals[day]) {
      dailyTotals[day] = 0;
    }

    dailyTotals[day] = calculationEngine.round(dailyTotals[day] + amount);
  });

  return dailyTotals;
};

/**
 * Get spending by week
 */
export const getWeeklySpending = (expenses, year, month) => {
  const monthlyExpenses = filterByMonth(expenses, year, month);
  const weeklyTotals = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };

  monthlyExpenses.forEach(expense => {
    const day = new Date(expense.date).getDate();
    const week = Math.ceil(day / 7);
    const amount = parseFloat(expense.amount || 0);

    weeklyTotals[week] = calculationEngine.round(weeklyTotals[week] + amount);
  });

  return weeklyTotals;
};

/**
 * Find highest spending day
 */
export const getHighestSpendingDay = (expenses, year, month) => {
  const dailySpending = getDailySpending(expenses, year, month);
  let maxDay = null;
  let maxAmount = 0;

  Object.entries(dailySpending).forEach(([day, amount]) => {
    if (amount > maxAmount) {
      maxAmount = amount;
      maxDay = parseInt(day);
    }
  });

  return {
    day: maxDay,
    amount: maxAmount,
    date: maxDay ? new Date(year, month, maxDay).toLocaleDateString() : null
  };
};

// ==================== BUDGET ANALYSIS ====================

/**
 * Compare budget vs actual spending for the month
 */
export const getBudgetVsActual = (budgets, expenses, year, month) => {
  const categorySpending = getCategoryBreakdown(expenses, year, month);
  const spendingByCategory = {};

  categorySpending.categories.forEach(cat => {
    spendingByCategory[cat.name] = cat.amount;
  });

  const comparison = budgets.map(budget => {
    const spent = spendingByCategory[budget.category] || 0;
    const budgetAmount = parseFloat(budget.amount || budget.limit || 0);
    const utilization = calculationEngine.calculateBudgetUtilization(budgetAmount, spent);

    return {
      category: budget.category,
      budgeted: budgetAmount,
      spent: spent,
      remaining: utilization.remaining,
      percentageUsed: utilization.percentageUsed,
      isOverBudget: utilization.isOverBudget,
      status: utilization.isOverBudget ? 'Over Budget' :
              utilization.percentageUsed >= 90 ? 'Critical' :
              utilization.percentageUsed >= 70 ? 'Warning' :
              'Good'
    };
  });

  return comparison.sort((a, b) => b.percentageUsed - a.percentageUsed);
};

/**
 * Calculate remaining budget for the month
 */
export const getRemainingBudget = (budgets, expenses, year, month) => {
  const totalBudget = calculationEngine.calculateTotalBudget(budgets);
  const monthlyExpenses = calculateMonthlyExpenses(expenses, year, month).total;
  const remaining = calculationEngine.subtract(totalBudget, monthlyExpenses);
  const percentageUsed = calculationEngine.percentageOf(monthlyExpenses, totalBudget);

  return {
    totalBudget,
    spent: monthlyExpenses,
    remaining,
    percentageUsed,
    isOverBudget: remaining < 0
  };
};

// ==================== MONTHLY SUMMARY ====================

/**
 * Generate complete monthly financial summary
 * This is the master function for monthly tracking
 */
export const generateMonthlySummary = ({
  incomes = [],
  expenses = [],
  budgets = [],
  year,
  month,
  taxRate = 0,
  country = null
}) => {
  // Basic totals
  const incomeData = calculateMonthlyIncome(incomes, year, month);
  const expenseData = calculateMonthlyExpenses(expenses, year, month);
  const taxAmount = calculateMonthlyTax(incomes, year, month, taxRate);
  const netIncome = calculationEngine.calculateNetAfterTax(incomeData.total, taxRate);
  const netBalance = calculationEngine.subtract(netIncome, expenseData.total);

  // Category analysis
  const categoryBreakdown = getCategoryBreakdown(expenses, year, month);
  const topCategories = getTopCategories(expenses, year, month, 5);

  // Spending patterns
  const dailyAverage = getDailyAverage(expenses, year, month);
  const highestSpendingDay = getHighestSpendingDay(expenses, year, month);
  const weeklySpendingMap = getWeeklySpending(expenses, year, month);
  const weeklySpending = Object.entries(weeklySpendingMap).map(([week, amount]) => ({
    week: `Week ${week}`,
    amount,
  }));
  const sourceBreakdown = getSourceBreakdown(expenseData.transactions);
  const sourceCategoryBreakdown = getSourceCategoryBreakdown(expenseData.transactions);

  // Budget analysis
  const budgetVsActual = getBudgetVsActual(budgets, expenses, year, month);
  const remainingBudget = getRemainingBudget(budgets, expenses, year, month);
  const overBudgetCategories = budgetVsActual
    .filter((budget) => budget.isOverBudget)
    .map((budget) => ({
      category: budget.category,
      over: Math.abs(budget.remaining),
      spent: budget.spent,
      budget: budget.budgeted,
    }));
  const budgetAnalysis = {
    comparison: budgetVsActual.map((budget) => ({
      ...budget,
      budget: budget.budgeted,
    })),
    totalRemaining: remainingBudget.remaining,
    overallStatus: remainingBudget.isOverBudget
      ? 'Over'
      : remainingBudget.percentageUsed >= 90
        ? 'Critical'
        : remainingBudget.percentageUsed >= 70
          ? 'Warning'
          : 'Good',
    overBudgetCategories,
  };

  // Calculate savings rate
  const savingsRate = calculationEngine.calculateSavingsRate(netIncome, expenseData.total);
  const trends = {
    comparison: buildTrendComparison(incomes, expenses, year, month),
  };

  // Month info
  const monthName = new Date(year, month, 1).toLocaleString('default', { month: 'long' });
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const currentDay = new Date().getDate();
  const daysRemaining = month === new Date().getMonth() && year === new Date().getFullYear()
    ? daysInMonth - currentDay
    : 0;

  return {
    // Period info
    period: {
      year,
      month,
      monthName,
      yearMonth: `${year}-${String(month + 1).padStart(2, '0')}`,
      daysInMonth,
      daysRemaining,
      isCurrentMonth: month === new Date().getMonth() && year === new Date().getFullYear()
    },

    // Financial totals
    totals: {
      grossIncome: calculationEngine.round(incomeData.total),
      tax: calculationEngine.round(taxAmount),
      netIncome: calculationEngine.round(netIncome),
      expenses: calculationEngine.round(expenseData.total),
      netBalance: calculationEngine.round(netBalance),
      savingsRate: calculationEngine.round(savingsRate),
      totalIncome: calculationEngine.round(incomeData.total),
      totalExpenses: calculationEngine.round(expenseData.total),
      totalTax: calculationEngine.round(taxAmount),
      remainingBalance: calculationEngine.round(netBalance),
    },

    // Transaction counts
    counts: {
      income: incomeData.count,
      expenses: expenseData.count,
      total: incomeData.count + expenseData.count
    },

    // Category breakdown
    categories: categoryBreakdown.categories.map(({ name, ...data }) => ({
      category: name,
      ...data,
    })),
    categorySummary: {
      breakdown: categoryBreakdown.categories,
      top: topCategories,
      total: categoryBreakdown.total,
      count: categoryBreakdown.categoryCount
    },

    // Spending patterns
    patterns: {
      dailyAverage: calculationEngine.round(dailyAverage),
      weeklySpending,
      weeklySpendingMap,
      highestDay: highestSpendingDay,
      highestSpendingDay,
      dailySpending: getDailySpending(expenses, year, month)
    },

    // Budget analysis
    budget: {
      comparison: budgetVsActual,
      remaining: remainingBudget,
      overBudgetCategories: budgetVsActual.filter(b => b.isOverBudget).length
    },
    budgetAnalysis,

    sourceAnalysis: {
      breakdown: sourceBreakdown,
      categories: sourceCategoryBreakdown,
    },

    // Tax info
    tax: {
      rate: taxRate,
      amount: calculationEngine.round(taxAmount),
      country: country
    },

    // Transactions
    transactionGroups: {
      income: incomeData.transactions,
      expenses: expenseData.transactions,
      all: [...incomeData.transactions, ...expenseData.transactions].sort((a, b) =>
        new Date(b.date) - new Date(a.date)
      )
    },
    transactions: [...expenseData.transactions].sort((a, b) => new Date(b.date) - new Date(a.date)),

    trends,

    // Status indicators
    status: {
      isPositive: netBalance > 0,
      isOverBudget: remainingBudget.isOverBudget,
      healthScore: calculateHealthScore({
        savingsRate,
        isOverBudget: remainingBudget.isOverBudget,
        netBalance
      })
    }
  };
};

// ==================== HEALTH SCORE ====================

/**
 * Calculate monthly financial health score (0-100)
 */
const calculateHealthScore = ({ savingsRate, isOverBudget, netBalance }) => {
  let score = 100;

  // Deduct for negative balance
  if (netBalance < 0) score -= 40;

  // Deduct for low savings rate
  if (savingsRate < 0) score -= 30;
  else if (savingsRate < 10) score -= 20;
  else if (savingsRate < 20) score -= 10;

  // Deduct for being over budget
  if (isOverBudget) score -= 20;

  return Math.max(0, Math.min(100, score));
};

// ==================== TREND ANALYSIS ====================

/**
 * Compare current month with previous month
 */
export const compareWithPreviousMonth = ({
  incomes,
  expenses,
  budgets,
  taxRate,
  country
}) => {
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();

  const previousMonth = currentMonth === 0 ? 11 : currentMonth - 1;
  const previousYear = currentMonth === 0 ? currentYear - 1 : currentYear;

  const current = generateMonthlySummary({
    incomes,
    expenses,
    budgets,
    year: currentYear,
    month: currentMonth,
    taxRate,
    country
  });

  const previous = generateMonthlySummary({
    incomes,
    expenses,
    budgets,
    year: previousYear,
    month: previousMonth,
    taxRate,
    country
  });

  return {
    current,
    previous,
    changes: {
      income: calculationEngine.percentageChange(previous.totals.grossIncome, current.totals.grossIncome),
      expenses: calculationEngine.percentageChange(previous.totals.expenses, current.totals.expenses),
      savings: calculationEngine.percentageChange(previous.totals.netBalance, current.totals.netBalance),
      savingsRate: calculationEngine.subtract(current.totals.savingsRate, previous.totals.savingsRate)
    }
  };
};

// ==================== EXPORT ====================

const monthlyAnalysisService = {
  // Date utilities
  getCurrentMonth,
  getMonthBounds,
  formatYearMonth,
  isInMonth,
  getAvailableMonths,

  // Filtering
  filterByMonth,
  filterByTypeAndMonth,
  filterByDateRange,

  // Monthly totals
  calculateMonthlyIncome,
  calculateMonthlyExpenses,
  calculateMonthlyTax,

  // Category analysis
  getCategoryBreakdown,
  getTopCategories,

  // Spending patterns
  getDailyAverage,
  getDailySpending,
  getWeeklySpending,
  getHighestSpendingDay,

  // Budget analysis
  getBudgetVsActual,
  getRemainingBudget,

  // Monthly summary (master function)
  generateMonthlySummary,

  // Trends
  compareWithPreviousMonth
};

export default monthlyAnalysisService;
