# AtonixCorp App

A modern React-based personal finance management application with expense tracking, budgeting, income management, and analytics.

## Features

- 📊 **Dashboard**: Overview of your financial status with charts and recent transactions
- 💸 **Expense Tracking**: Add, view, and delete expenses by category
- 💵 **Income Management**: Track multiple income sources
- 📈 **Budget Management**: Set budget limits per category with visual progress tracking
- 📉 **Analytics**: Detailed insights with charts and spending patterns

## Getting Started

### Prerequisites

- Node.js 18, 20, or 21
- npm or yarn

This app includes an [.nvmrc](/Users/ofidohubvm/AtonixCorp/app/.nvmrc) file pinned to Node.js 20. If you use `nvm`, switch first:

```bash
nvm use
```

### Installation

1. Install dependencies:
```bash
nvm use
npm install
```

2. Start the development server:
```bash
nvm use
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `npm start` - Runs the app in development mode
- `npm build` - Builds the app for production
- `npm test` - Runs tests
- `npm eject` - Ejects from Create React App (irreversible)

## Tech Stack

- React 18
- React Router v6
- Recharts for data visualization
- Context API for state management
- CSS Modules for styling

## Project Structure

```
src/
├── components/
│   └── Layout/         # Navigation and layout
├── pages/
│   ├── Dashboard/      # Main dashboard
│   ├── Expenses/       # Expense management
│   ├── Income/         # Income tracking
│   ├── Budget/         # Budget planning
│   └── Analytics/      # Financial analytics
├── context/
│   └── FinanceContext.js  # Global state management
├── App.js              # Main app component
└── index.js            # Entry point
```

## Features in Detail

### State Management
Uses React Context API with the following operations:
- Add/Delete/Update Expenses
- Add/Delete/Update Income
- Add/Delete/Update Budgets
- Automatic calculations for totals and balances

## Runtime Data

Authenticated application data is loaded through the Django REST API and scoped
to the active organization or workspace. New features must use a typed API
service and persisted backend data; mock services, demo fallbacks, and fixture
records are not permitted in production paths.

## License

MIT License
