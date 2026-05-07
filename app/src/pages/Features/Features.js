import React from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './Features.css';

const Features = () => {
  const features = [
    {
      title: 'Smart Budgeting',
      description: 'AI-powered budgeting that learns from your spending patterns and suggests optimizations.',
      details: ['Automated categorization', 'Spending predictions', 'Budget alerts', 'Goal tracking']
    },
    {
      title: 'Advanced Analytics',
      description: 'Comprehensive financial analytics with real-time insights and predictive modeling.',
      details: ['Real-time dashboards', 'Trend analysis', 'Performance metrics', 'Custom reports']
    },
    {
      title: 'Multi-Currency Support',
      description: 'Seamlessly manage finances across 150+ currencies with automatic conversion.',
      details: ['Real-time rates', 'Currency hedging', 'FX risk management', 'Borderless transfers']
    },
    {
      title: 'Enterprise Management',
      description: 'Complete solution for managing complex business structures and multiple entities.',
      details: ['Multi-entity support', 'Department management', 'Role-based access', 'Compliance tracking']
    },
    {
      title: 'Tax Optimization',
      description: 'Automated tax calculation and optimization across 207 countries and jurisdictions.',
      details: ['Global tax compliance', 'Automated filings', 'Tax planning', 'Audit trails']
    },
    {
      title: 'Financial Modeling',
      description: 'Professional-grade financial modeling tools for investment analysis and planning.',
      details: ['DCF analysis', 'Comparable valuation', 'Scenario modeling', 'Risk assessment']
    },
    {
      title: 'Bank-Grade Security',
      description: 'Military-grade encryption and security protocols protecting your financial data.',
      details: ['256-bit encryption', 'Biometric auth', 'Multi-factor authentication', 'Real-time monitoring']
    },
    {
      title: 'AI Intelligence',
      description: 'Artificial intelligence that provides insights, predictions, and automated decisions.',
      details: ['Anomaly detection', 'Investment recommendations', 'Automated reporting', 'Market intelligence']
    },
    {
      title: 'Mobile Banking',
      description: 'Full-featured mobile app for managing finances on-the-go with biometric security.',
      details: ['Mobile payments', 'Biometric login', 'Offline mode', 'Push notifications']
    },
    {
      title: 'Team Collaboration',
      description: 'Collaborative tools for teams to work together on financial planning and analysis.',
      details: ['Shared workspaces', 'Document collaboration', 'Approval workflows', 'Audit logs']
    },
    {
      title: 'API Integration',
      description: 'Comprehensive API for integrating with other financial systems and services.',
      details: ['RESTful APIs', 'Webhook support', 'Third-party integrations', 'Developer tools']
    },
    {
      title: 'Compliance Automation',
      description: 'Automated compliance monitoring and reporting for regulatory requirements.',
      details: ['Regulatory reporting', 'Compliance alerts', 'Document management', 'Audit trails']
    }
  ];

  return (
    <div className="features-page">
      <Header />

      <section className="features-hero">
        <div className="hero-content">
          <h1>Powerful Features for Modern Finance</h1>
          <p>Discover the comprehensive suite of tools and capabilities that make
            Ledgora the leading choice for financial management.
          </p>
        </div>
      </section>

      <section className="features-grid">
        <div className="container">
          <div className="features-list">
            {features.map((feature, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon">
                  {feature.icon}
                </div>
                <div className="feature-content">
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                  <ul className="feature-details">
                    {feature.details.map((detail, idx) => (
                      <li key={idx}>{detail}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="features-showcase">
        <div className="container">
          <h2>Experience the Power of Atonix</h2>
          <div className="showcase-grid">
            <div className="showcase-item">
              <div className="showcase-image">

              </div>
              <h3>Real-Time Analytics</h3>
              <p>Get instant insights into your financial performance with live dashboards
                and automated reporting that updates in real-time.
              </p>
            </div>
            <div className="showcase-item">
              <div className="showcase-image">

              </div>
              <h3>Global Operations</h3>
              <p>Manage international finances effortlessly with support for 207 countries,
                150+ currencies, and automated cross-border transactions.
              </p>
            </div>
            <div className="showcase-item">
              <div className="showcase-image">

              </div>
              <h3>Enterprise Security</h3>
              <p>Your data is protected by bank-grade security with end-to-end encryption,
                biometric authentication, and continuous monitoring.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="features-cta">
        <div className="container">
          <h2>Ready to Experience These Features?</h2>
          <p>Start your free trial today and discover how Ledgora can transform your financial management.</p>
          <div className="cta-buttons">
            <Link to="/register" className="btn-primary btn-large">Start Free Trial
            </Link>
            <Link to="/pricing" className="btn-outline btn-large">View Pricing
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Features;