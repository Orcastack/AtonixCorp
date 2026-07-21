import React from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './Product.css';

const Product = () => {
  return (
    <div className="product-page">
      <Header />

      <section className="product-hero">
        <div className="hero-content">
          <h1>Financial Management Software Services</h1>
          <p>AtonixCorp brings personal finance, enterprise operations, global tax,
            security, and AI-powered financial intelligence into one platform.
          </p>
          <div className="hero-stats">
            <div className="stat">
              <span className="stat-number">$2.5B+</span>
              <span className="stat-label">Assets Under Management</span>
            </div>
            <div className="stat">
              <span className="stat-number">50+</span>
              <span className="stat-label">Countries Supported</span>
            </div>
            <div className="stat">
              <span className="stat-number">99.9%</span>
              <span className="stat-label">Uptime Guarantee</span>
            </div>
          </div>
        </div>
      </section>

      <section className="product-overview">
        <div className="container">
          <h2>Financial Services Built Into One Platform</h2>
          <div className="product-grid">
            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>Personal Finance</h3>
              <p>Take control of your personal finances with intelligent budgeting,
                expense tracking, and investment management tools.
              </p>
              <ul className="product-features">
                <li>Smart budgeting & forecasting</li>
                <li>Multi-currency support</li>
                <li>Tax optimization</li>
                <li>Investment tracking</li>
              </ul>
            </div>

            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>Enterprise Solutions</h3>
              <p>Powerful tools for businesses to manage complex financial operations
                across multiple entities and jurisdictions.
              </p>
              <ul className="product-features">
                <li>Multi-entity management</li>
                <li>Global tax compliance</li>
                <li>Cash flow forecasting</li>
                <li>Risk management</li>
              </ul>
            </div>

            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>Global Reach</h3>
              <p>Operate seamlessly across borders with comprehensive international
                financial management and regulatory compliance.
              </p>
              <ul className="product-features">
                <li>207 countries supported</li>
                <li>Multi-currency transactions</li>
                <li>Cross-border payments</li>
                <li>International tax filing</li>
              </ul>
            </div>

            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>Bank-Grade Security</h3>
              <p>Your financial data is protected with military-grade encryption,
                biometric authentication, and advanced threat detection.
              </p>
              <ul className="product-features">
                <li>256-bit encryption</li>
                <li>Biometric authentication</li>
                <li>Real-time monitoring</li>
                <li>Compliance certified</li>
              </ul>
            </div>

            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>AI-Powered Insights</h3>
              <p>Leverage artificial intelligence for financial predictions,
                anomaly detection, and personalized recommendations.
              </p>
              <ul className="product-features">
                <li>Predictive analytics</li>
                <li>Automated reporting</li>
                <li>Risk assessment</li>
                <li>Market intelligence</li>
              </ul>
            </div>

            <div className="product-card">
              <div className="product-icon">

              </div>
              <h3>Expert Support</h3>
              <p>Get help from our team of financial experts and dedicated
                support specialists whenever you need assistance.
              </p>
              <ul className="product-features">
                <li>24/7 customer support</li>
                <li>Financial advisors</li>
                <li>Tax specialists</li>
                <li>Technical support</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="product-cta">
        <div className="container">
          <h2>Ready to Transform Your Financial Management?</h2>
          <p>Join thousands of users who trust AtonixCorp for their financial needs.</p>
          <div className="cta-buttons">
            <Link to="/register" className="btn-primary btn-large">Start Free Trial
            </Link>
            <Link to="/features" className="btn-outline btn-large">Explore Features
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Product;