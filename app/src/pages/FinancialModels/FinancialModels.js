import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useFinance } from '../../context/FinanceContext';
import { getApiBaseUrl } from '../../utils/apiBaseUrl';
import ModelInputForm from './components/ModelInputForm';
import ResultsDashboard from './components/ResultsDashboard';
import ScenarioDashboard from './components/ScenarioDashboard';
import ReportViewer from './components/ReportViewer';
import AnalyticsDashboard from './components/AnalyticsDashboard';

/**
 * Main Financial Models Page
 * Orchestrates model creation, execution, results viewing, and reporting
 * Integrates all backend calculation engines
 */
const FinancialModels = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    models,
    currentModel,
    modelTemplates,
    scenarios,
    aiInsights,
    reports,
    loading,
    error,
    loadModelTemplates,
    loadFinancialModels,
    createFinancialModel,
    calculateFinancialModel,
    loadScenarios,
    loadAIInsights,
    loadReports
  } = useFinance();

  // UI State Management
  const [activeTab, setActiveTab] = useState('input'); // input, results, scenarios, reports, analytics
  const [modelInputData, setModelInputData] = useState(null);
  const [calculationResults, setCalculationResults] = useState(null);
  const [scenarioResults, setScenarioResults] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculationError, setCalculationError] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        await loadModelTemplates();
        await loadFinancialModels();
        await loadReports();
      } catch (err) {
        console.error('Error loading initial data:', err);
      }
    };

    loadInitialData();
  }, [loadModelTemplates, loadFinancialModels, loadReports]);

  // Redirect to login if not authenticated
  if (!user) {
    navigate('/login');
    return null;
  }

  /**
   * Handle model input form submission
   * Triggers calculation engine and processes results
   */
  const handleModelSubmit = async (formData) => {
    try {
      setIsCalculating(true);
      setCalculationError(null);

      // Store input data
      setModelInputData(formData);

      // Create financial model via API
      const modelData = {
        name: formData.modelName || `Model ${new Date().toLocaleString()}`,
        model_type: formData.modelType,
        input_data: formData,
        assumptions: formData.assumptions || {},
        organization: formData.organizationId, // If enterprise mode
        template: formData.templateId // If using template
      };

      const createdModel = await createFinancialModel(modelData);

      // Calculate the model
      const results = await calculateFinancialModel(createdModel.id);

      // Process results
      setCalculationResults(results.results);
      setSelectedModel(createdModel.id);

      // Load related data
      await loadScenarios(createdModel.id);
      await loadAIInsights();

      // Auto-switch to results tab
      setActiveTab('results');

      // Log successful calculation
      console.log('Model calculation completed', {
        modelId: createdModel.id,
        timestamp: new Date().toISOString(),
        resultsKeys: Object.keys(results.results || {}),
      });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Model calculation error:', err);
    } finally {
      setIsCalculating(false);
    }
  };

  /**
   * Handle scenario analysis request
   * Generates best/base/worst case scenarios
   */
  const handleScenarioAnalysis = async () => {
    try {
      setIsCalculating(true);
      setCalculationError(null);

      if (!selectedModel) {
        throw new Error('No model selected');
      }

      // Create scenarios via API
      const scenarioData = [
        {
          name: 'Best Case',
          scenario_type: 'best',
          financial_model: selectedModel,
          assumptions_override: {
            revenue_growth: 1.5, // 50% higher growth
            cost_reduction: 0.8, // 20% cost reduction
            discount_rate: 0.08 // Lower discount rate
          }
        },
        {
          name: 'Base Case',
          scenario_type: 'base',
          financial_model: selectedModel,
          assumptions_override: {} // Use model defaults
        },
        {
          name: 'Worst Case',
          scenario_type: 'worst',
          financial_model: selectedModel,
          assumptions_override: {
            revenue_growth: 0.7, // 30% lower growth
            cost_increase: 1.3, // 30% cost increase
            discount_rate: 0.15 // Higher discount rate
          }
        }
      ];

      // Create scenarios and run analysis
      const scenarioPromises = scenarioData.map(async (scenario) => {
        const created = await scenariosAPI.create(scenario);
        const result = await scenariosAPI.runScenario(created.data.id);
        return result.data;
      });

      const scenarioResults = await Promise.all(scenarioPromises);

      // Process results
      setScenarioResults(scenarioResults);

      // Auto-switch to scenarios tab
      setActiveTab('scenarios');

      // Log successful scenario analysis
      console.log('Scenario analysis completed', {
        modelId: selectedModel,
        scenariosCount: scenarioResults.length,
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Scenario analysis error:', err);
    } finally {
      setIsCalculating(false);
    }
  };

      const scenarios = await response.json();
      setScenarioResults(scenarios);
      setActiveTab('scenarios');

      console.log('Scenario analysis completed', {
        scenarios: Object.keys(scenarios.scenarios || {}),
      });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Scenario analysis error:', err);
    } finally {
      setIsCalculating(false);
    }
  };

  /**
   * Handle report generation
   * Generates formatted reports with visualizations
   */
  const handleGenerateReport = async (reportType = 'executive') => {
    try {
      setIsCalculating(true);
      setCalculationError(null);

      if (!calculationResults) {
        throw new Error('No model calculated yet');
      }

      // Call reporting engine
      const response = await fetch(`${getApiBaseUrl()}/models/reports/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          modelId: selectedModel,
          results: calculationResults,
          scenarios: scenarioResults,
          type: reportType,
        }),
      });

      if (!response.ok) {
        throw new Error(`Report generation failed: ${response.statusText}`);
      }

      const report = await response.json();
      setReportData(report);
      setActiveTab('reports');

      console.log('Report generated', {
        reportType,
        reportId: report.id,
      });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Report generation error:', err);
    } finally {
      setIsCalculating(false);
    }
  };

  /**
   * Handle analytics dashboard update
   * Loads KPI dashboards and trend analysis
   */
  const handleLoadAnalytics = async () => {
    try {
      setIsCalculating(true);
      setCalculationError(null);

      if (!calculationResults) {
        throw new Error('No model calculated yet');
      }

      // Call advanced reporting engine
      const response = await fetch(`${getApiBaseUrl()}/models/analytics/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          modelId: selectedModel,
          results: calculationResults,
        }),
      });

      if (!response.ok) {
        throw new Error(`Analytics loading failed: ${response.statusText}`);
      }

      const analytics = await response.json();
      setAnalyticsData(analytics);
      setActiveTab('analytics');

      console.log('Analytics loaded', {
        kpis: analytics.kpis?.length || 0,
        trends: Object.keys(analytics.trends || {}),
      });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Analytics loading error:', err);
    } finally {
      setIsCalculating(false);
    }
  };

  /**
   * Export results to various formats
   */
  const handleExportResults = async (format = 'json') => {
    try {
      if (!calculationResults) {
        throw new Error('No results to export');
      }

      const exportData = {
        timestamp: new Date().toISOString(),
        userId: user.id,
        modelId: selectedModel,
        input: modelInputData,
        results: calculationResults,
        scenarios: scenarioResults,
        reports: reportData,
        analytics: analyticsData,
      };

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `financial-model-${selectedModel}-${Date.now()}.json`;
        link.click();
      } else if (format === 'csv') {
        // Convert to CSV format
        let csv = 'Category,Item,Value\n';
        const flattenObject = (obj, prefix = '') => {
          for (const key in obj) {
            if (typeof obj[key] === 'object') {
              flattenObject(obj[key], `${prefix}${key}.`);
            } else {
              csv += `${prefix}${key},${obj[key]}\n`;
            }
          }
        };
        flattenObject(calculationResults);

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `financial-model-${selectedModel}-${Date.now()}.csv`;
        link.click();
      }

      console.log('Results exported', { format });
    } catch (err) {
      setCalculationError(err.message);
      console.error('Export error:', err);
    }
  };

  return (
    <div className="financial-models-container">
      <header className="models-header">
        <div className="header-content">
          <h1>Financial Modeling Engine</h1>
          <p className="subtitle">Advanced financial analysis and strategic planning</p>
        </div>
        <div className="header-stats">
          <div className="stat-card">
            <span className="stat-label">Models</span>
            <span className="stat-value">{models?.length || 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Current</span>
            <span className="stat-value">{selectedModel ? '' : '-'}</span>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'input' ? 'active' : ''}`}
          onClick={() => setActiveTab('input')}
          disabled={isCalculating}
        >
          <span className="tab-icon"></span>
          <span className="tab-label">Input</span>
        </button>

        <button
          className={`tab-button ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
          disabled={!calculationResults || isCalculating}
        >
          <span className="tab-icon"></span>
          <span className="tab-label">Results</span>
        </button>

        <button
          className={`tab-button ${activeTab === 'scenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('scenarios')}
          disabled={!calculationResults || isCalculating}
        >
          <span className="tab-icon"></span>
          <span className="tab-label">Scenarios</span>
        </button>

        <button
          className={`tab-button ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
          disabled={!calculationResults || isCalculating}
        >
          <span className="tab-icon"></span>
          <span className="tab-label">Reports</span>
        </button>

        <button
          className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
          disabled={!calculationResults || isCalculating}
        >
          <span className="tab-icon"></span>
          <span className="tab-label">Analytics</span>
        </button>
      </nav>

      {/* Error Display */}
      {(error || calculationError) && (
        <div className="error-banner">
          <span className="error-icon"></span>
          <div className="error-content">
            <h3>Error</h3>
            <p>{error || calculationError}</p>
          </div>
          <button
            className="error-close"
            onClick={() => {
              setCalculationError(null);
            }}
          >

          </button>
        </div>
      )}

      {/* Loading State */}
      {isCalculating && (
        <div className="loading-overlay">
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Processing financial model...</p>
          </div>
        </div>
      )}

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'input' && (
          <div className="tab-pane active">
            <ModelInputForm
              onSubmit={handleModelSubmit}
              isLoading={isCalculating}
              initialData={modelInputData}
            />
          </div>
        )}

        {activeTab === 'results' && calculationResults && (
          <div className="tab-pane active">
            <ResultsDashboard
              results={calculationResults}
              inputData={modelInputData}
              onScenarioAnalysis={handleScenarioAnalysis}
              onGenerateReport={handleGenerateReport}
              onLoadAnalytics={handleLoadAnalytics}
              onExport={handleExportResults}
              isLoading={isCalculating}
            />
          </div>
        )}

        {activeTab === 'scenarios' && scenarioResults && (
          <div className="tab-pane active">
            <ScenarioDashboard
              scenarios={scenarioResults}
              baselineResults={calculationResults}
              onGenerateReport={handleGenerateReport}
              isLoading={isCalculating}
            />
          </div>
        )}

        {activeTab === 'reports' && reportData && (
          <div className="tab-pane active">
            <ReportViewer
              report={reportData}
              onExport={handleExportResults}
              isLoading={isCalculating}
            />
          </div>
        )}

        {activeTab === 'analytics' && analyticsData && (
          <div className="tab-pane active">
            <AnalyticsDashboard
              analytics={analyticsData}
              results={calculationResults}
              isLoading={isCalculating}
            />
          </div>
        )}
      </div>

      {/* Floating Action Button */}
      <div className="fab-container">
        <button
          className={`fab ${isCalculating ? 'disabled' : ''}`}
          onClick={() => setActiveTab('input')}
          title="New Model"
          disabled={isCalculating}
        >
          <span className="fab-icon"></span>
        </button>
      </div>
    </div>
  );
};

export default FinancialModels;
