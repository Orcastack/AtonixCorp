import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFinance } from '../../context/FinanceContext';
import { useLanguage } from '../../context/LanguageContext';
import './Dashboard.css';

const sidebarItems = [
  { label: 'Search', route: '/app/organizations/select' },
  { label: 'Budget Calculator', route: '/budget' },
  { label: 'Set New Goal', route: '/help-center' },
  { label: 'Ask Coach', route: '/support-center' },
  { label: 'Courses', route: '/help-center' },
  { label: 'Inbox', route: '/support-tickets' },
  { label: 'Help Center', route: '/help-center' },
  { label: 'Settings', route: '/security-center' },
];

const topicTabs = ['All Topics', 'Budgeting', 'Saving', 'Investing'];

const courseCatalog = [
  {
    title: 'Budgeting Foundations',
    topic: 'Budgeting',
    level: 'Beginner',
    description: 'Build a stable monthly budget that supports disciplined spending and measurable savings.',
    duration: '18 min',
    sections: 5,
  },
  {
    title: 'Saving Systems',
    topic: 'Saving',
    level: 'Intermediate',
    description: 'Set up simple savings routines with progress checkpoints and calm, predictable momentum.',
    duration: '24 min',
    sections: 6,
  },
  {
    title: 'Cash Flow Discipline',
    topic: 'Budgeting',
    level: 'Intermediate',
    description: 'Track income and expenses with a clean structure that keeps decisions easy to review.',
    duration: '22 min',
    sections: 4,
  },
  {
    title: 'Investing Basics',
    topic: 'Investing',
    level: 'Advanced',
    description: 'Understand risk, allocation, and compounding through a controlled institutional framework.',
    duration: '30 min',
    sections: 7,
  },
];

const moduleTiles = [
  { label: 'Budget Calculator', description: 'Review projected cash flow and basic spending discipline.', route: '/budget' },
  { label: 'Savings Tracker', description: 'Follow the savings progress bar and keep targets visible.', route: '/help-center' },
  { label: 'Ask Coach', description: 'Use the support center for guided financial help.', route: '/support-center' },
  { label: 'Learning Library', description: 'Move through the course catalog without leaving the dashboard.', route: '/help-center' },
  { label: 'Inbox', description: 'Check notifications and unresolved financial tasks.', route: '/support-tickets' },
  { label: 'Settings', description: 'Adjust institutional controls and security preferences.', route: '/security-center' },
];

const formatMoney = (value) => `$${Number(value || 0).toFixed(2)}`;

const Dashboard = () => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const {
    totalIncome,
    totalExpenses,
    balance,
    expenses,
    budgets,
    monthlySummary,
    selectedMonth,
    availableMonths,
    changeMonth,
    financialSummary,
    validationResults,
    expenseSourceFilter,
    setExpenseSourceFilter,
  } = useFinance();

  const [viewMode, setViewMode] = useState('monthly');
  const [activeTopic, setActiveTopic] = useState('All Topics');

  const displayData = useMemo(() => {
    if (viewMode === 'monthly' && monthlySummary) {
      return {
        income: monthlySummary.totals?.totalIncome || 0,
        expenses: monthlySummary.totals?.totalExpenses || 0,
        balance: monthlySummary.totals?.remainingBalance || 0,
        tax: monthlySummary.totals?.totalTax || 0,
        netIncome: monthlySummary.totals?.netIncome || 0,
        categoryData: Array.isArray(monthlySummary.categories) ? monthlySummary.categories : [],
        budgetComparison: Array.isArray(monthlySummary.budgetAnalysis?.comparison) ? monthlySummary.budgetAnalysis.comparison : [],
        recentTransactions: Array.isArray(monthlySummary.transactions) ? monthlySummary.transactions : [],
      };
    }

    const categoryData = Array.isArray(expenses)
      ? expenses.reduce((accumulator, expense) => {
          const existing = accumulator.find((item) => item.category === expense.category);
          if (existing) {
            existing.amount += expense.amount;
          } else {
            accumulator.push({ category: expense.category, amount: expense.amount });
          }
          return accumulator;
        }, [])
      : [];

    const budgetComparison = Array.isArray(budgets)
      ? budgets.map((budget) => {
          const spent = (Array.isArray(expenses) ? expenses : [])
            .filter((expense) => expense.category === budget.category)
            .reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
          return {
            category: budget.category,
            budget: budget.limit || 0,
            spent,
            remaining: (budget.limit || 0) - spent,
          };
        })
      : [];

    return {
      income: totalIncome || 0,
      expenses: totalExpenses || 0,
      balance: balance || 0,
      tax: financialSummary?.tax?.amount || 0,
      netIncome: financialSummary?.income?.net || 0,
      categoryData,
      budgetComparison,
      recentTransactions: Array.isArray(expenses)
        ? [...expenses].sort((left, right) => new Date(right.date) - new Date(left.date)).slice(0, 5)
        : [],
    };
  }, [balance, budgets, expenses, financialSummary, monthlySummary, selectedMonth, totalExpenses, totalIncome, viewMode]);

  const budgetAlertDetails = Array.isArray(validationResults?.warningDetails)
    ? validationResults.warningDetails
    : [];

  const savingsValue = Math.max(displayData.balance, 0);
  const savingsProgress = displayData.income > 0 ? Math.min(100, Math.round((savingsValue / displayData.income) * 100)) : 0;
  const learningProgress = Math.min(100, Math.max(18, (monthlySummary?.categories?.length || displayData.recentTransactions.length || 0) * 12));
  const modulesCompleted = Math.max(1, (budgets?.length || 0) + (displayData.recentTransactions.length || 0));
  const streakValue = Math.max(1, availableMonths.length || 1);
  const levelValue = Math.min(9, Math.max(1, Math.round(((validationResults?.healthScore || 72) / 10))));
  const filteredCourses = activeTopic === 'All Topics'
    ? courseCatalog
    : courseCatalog.filter((course) => course.topic === activeTopic);

  const overviewCards = [
    {
      title: viewMode === 'monthly' ? 'Monthly Income' : 'Total Income',
      value: formatMoney(displayData.income),
      label: viewMode === 'monthly' ? 'Current period income' : 'All-time income total',
      tone: 'blue',
      progress: 100,
    },
    {
      title: viewMode === 'monthly' ? 'Monthly Savings' : 'Total Savings',
      value: formatMoney(savingsValue),
      label: 'Amount retained after expenses',
      tone: 'green',
      progress: savingsProgress,
    },
    {
      title: 'Savings Progress',
      value: `${savingsProgress}%`,
      label: 'Progress toward disciplined saving',
      tone: 'gray',
      progress: savingsProgress,
    },
    {
      title: 'Learning Progress',
      value: `${learningProgress}%`,
      label: 'Current financial learning momentum',
      tone: 'purple',
      progress: learningProgress,
    },
  ];

  const quickStats = [
    { label: 'Streak', value: `${streakValue} months` },
    { label: 'Modules completed', value: String(modulesCompleted) },
    { label: 'Level', value: `Lv. ${levelValue}` },
  ];

  const goTo = (route) => {
    navigate(route);
  };

  return (
    <div className="dashboard-finance-page" key={selectedMonth?.month || 'dashboard'}>
      <aside className="dashboard-sidebar">
        <div className="dashboard-sidebar-brand">
          <span className="dashboard-sidebar-brand-mark">LGX</span>
          <div>
            <div className="dashboard-sidebar-brand-name">Ledgora</div>
            <div className="dashboard-sidebar-brand-subtitle">Financial Dashboard</div>
          </div>
        </div>

        <nav className="dashboard-sidebar-nav" aria-label="Dashboard navigation">
          {sidebarItems.map((item) => (
            <button
              key={item.label}
              className="dashboard-sidebar-item"
              onClick={() => goTo(item.route)}
              type="button"
            >
              <span className="dashboard-sidebar-icon" aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="dashboard-main-column">
        <header className="dashboard-top-header">
          <div className="dashboard-top-copy">
            <p className="dashboard-top-kicker">Ledgora Financial Console</p>
            <h1 className="dashboard-top-title">{t('dashboard.title')}</h1>
            <p className="dashboard-top-subtitle">
              Clean oversight for income, savings, learning, and financial discipline.
            </p>
          </div>

          <div className="dashboard-top-stats" aria-label="Dashboard quick stats">
            {quickStats.map((item) => (
              <div className="dashboard-stat" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </header>

        <main className="dashboard-content">
          <section className="dashboard-section">
            <div className="dashboard-section-header">
              <div>
                <h2 className="dashboard-section-title">Overview</h2>
                <p className="dashboard-section-subtitle">At-a-glance metrics with calm, institutional presentation.</p>
              </div>
              <div className="dashboard-filters">
                <div className="dashboard-toggle-group" role="tablist" aria-label="Dashboard view mode">
                  <button
                    type="button"
                    className={`dashboard-toggle${viewMode === 'monthly' ? ' active' : ''}`}
                    onClick={() => setViewMode('monthly')}
                  >
                    {t('dashboard.monthlyView')}
                  </button>
                  <button
                    type="button"
                    className={`dashboard-toggle${viewMode === 'all-time' ? ' active' : ''}`}
                    onClick={() => setViewMode('all-time')}
                  >
                    {t('dashboard.allTime')}
                  </button>
                </div>

                <div className="dashboard-toggle-group" role="tablist" aria-label="Expense source filter">
                  {['all', 'manual', 'imported'].map((value) => (
                    <button
                      key={value}
                      type="button"
                      className={`dashboard-toggle${expenseSourceFilter === value ? ' active' : ''}`}
                      onClick={() => setExpenseSourceFilter(value)}
                    >
                      {value === 'all' ? 'All Sources' : value === 'manual' ? 'Manual Only' : 'Imported Only'}
                    </button>
                  ))}
                </div>

                {viewMode === 'monthly' && availableMonths.length > 0 && (
                  <select
                    className="dashboard-month-select"
                    value={`${selectedMonth.year}-${selectedMonth.month}`}
                    onChange={(event) => {
                      const [year, month] = event.target.value.split('-');
                      changeMonth(Number(year), Number(month));
                    }}
                  >
                    {availableMonths.map((monthItem) => (
                      <option key={`${monthItem.year}-${monthItem.month}`} value={`${monthItem.year}-${monthItem.month}`}>
                        {new Date(monthItem.year, monthItem.month, 1).toLocaleString([], { month: 'long' })} {monthItem.year}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="dashboard-overview-grid">
              {overviewCards.map((card) => (
                <article key={card.title} className={`dashboard-overview-card dashboard-overview-card--${card.tone}`}>
                  <span className="dashboard-overview-title">{card.title}</span>
                  <strong className="dashboard-overview-value">{card.value}</strong>
                  <span className="dashboard-overview-label">{card.label}</span>
                  <div className="dashboard-progress" aria-hidden="true">
                    <span style={{ width: `${card.progress}%` }} />
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="dashboard-section">
            <div className="dashboard-section-header dashboard-section-header--stacked">
              <div>
                <h2 className="dashboard-section-title">Learning Opportunities</h2>
                <p className="dashboard-section-subtitle">A calm financial academy with predictable course cards and clear actions.</p>
              </div>
              <div className="dashboard-tabs" role="tablist" aria-label="Learning topics">
                {topicTabs.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    className={`dashboard-tab${activeTopic === tab ? ' active' : ''}`}
                    onClick={() => setActiveTopic(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="dashboard-course-grid">
              {filteredCourses.map((course) => (
                <article key={course.title} className="dashboard-course-card">
                  <div className="dashboard-course-meta">
                    <span>{course.level}</span>
                    <span>{course.duration}</span>
                  </div>
                  <h3>{course.title}</h3>
                  <p>{course.description}</p>
                  <div className="dashboard-course-footer">
                    <span>{course.sections} sections</span>
                    <button type="button" className="dashboard-link-button" onClick={() => goTo('/help-center')}>
                      Start Learning
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="dashboard-section">
            <div className="dashboard-section-header dashboard-section-header--stacked">
              <div>
                <h2 className="dashboard-section-title">Financial Modules</h2>
                <p className="dashboard-section-subtitle">Clean, reusable module cards for the main dashboard shell.</p>
              </div>
            </div>

            <div className="dashboard-module-grid">
              {moduleTiles.map((module) => (
                <article key={module.label} className="dashboard-module-card">
                  <h3>{module.label}</h3>
                  <p>{module.description}</p>
                  <button type="button" className="dashboard-link-button" onClick={() => goTo(module.route)}>
                    View Details
                  </button>
                </article>
              ))}
            </div>
          </section>

          <section className="dashboard-section dashboard-dual-grid">
            <article className="dashboard-panel">
              <div className="dashboard-section-header dashboard-section-header--compact">
                <div>
                  <h2 className="dashboard-section-title">Recent Transactions</h2>
                  <p className="dashboard-section-subtitle">The latest activity from the selected reporting mode.</p>
                </div>
              </div>

              {displayData.recentTransactions.length > 0 ? (
                <div className="dashboard-transaction-list">
                  {displayData.recentTransactions.map((transaction) => (
                    <div key={transaction.id} className="dashboard-transaction">
                      <div>
                        <strong>{transaction.description}</strong>
                        <span>{new Date(transaction.date).toLocaleDateString()}</span>
                      </div>
                      <div>
                        <span className="dashboard-transaction-badge">{transaction.category}</span>
                        <span className="dashboard-transaction-amount">-${Number(transaction.amount || 0).toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <h3>No transactions yet</h3>
                  <p>Add activity to see the transaction list populate here.</p>
                </div>
              )}
            </article>

            <article className="dashboard-panel">
              <div className="dashboard-section-header dashboard-section-header--compact">
                <div>
                  <h2 className="dashboard-section-title">Budget Alerts</h2>
                  <p className="dashboard-section-subtitle">Calm, solvable alerts with institutional visual treatment.</p>
                </div>
              </div>

              {budgetAlertDetails.length > 0 ? (
                <div className="dashboard-alert-list">
                  {budgetAlertDetails.slice(0, 3).map((alert) => (
                    <div key={alert.category} className={`dashboard-alert dashboard-alert--${alert.severity}`}>
                      <strong>{alert.category}</strong>
                      <p>{alert.message}</p>
                      <span>{alert.dominantSource?.label || 'Mixed sources'}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <h3>No budget alerts</h3>
                  <p>Your budget review is currently clean.</p>
                </div>
              )}
            </article>
          </section>

          {validationResults?.anomalies && validationResults.anomalies.length > 0 && (
            <section className="dashboard-section">
              <div className="dashboard-section-header dashboard-section-header--compact">
                <div>
                  <h2 className="dashboard-section-title">AI-Detected Anomalies</h2>
                  <p className="dashboard-section-subtitle">Highlighted carefully so they remain clear and non-alarming.</p>
                </div>
              </div>
              <div className="dashboard-alert-list">
                {validationResults.anomalies.map((anomaly, index) => (
                  <div key={`${anomaly.type}-${index}`} className={`dashboard-alert dashboard-alert--${anomaly.severity || 'medium'}`}>
                    <strong>{anomaly.type}</strong>
                    <p>{anomaly.message}</p>
                    {anomaly.suggestion && <span>{anomaly.suggestion}</span>}
                  </div>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
