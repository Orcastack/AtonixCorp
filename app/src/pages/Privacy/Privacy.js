import React from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';

const Privacy = () => {
  const sections = [
    {
      title: "Information We Collect",
      content: [
        "Personal information you provide (name, email, phone, address)",
        "Financial information for account verification and transactions",
        "Device and usage information for security and analytics",
        "Communication records when you contact our support team"
      ]
    },
    {
      title: "How We Use Your Information",
      content: [
        "Provide and maintain our financial services",
        "Verify your identity and prevent fraud",
        "Communicate with you about your account and services",
        "Improve our platform and develop new features",
        "Comply with legal and regulatory requirements"
      ]
    },
    {
      title: "Your Rights and Choices",
      content: [
        "Access and update your personal information",
        "Request deletion of your data (subject to legal requirements)",
        "Opt out of marketing communications",
        "Data portability and transfer rights",
        "Withdraw consent for data processing"
      ]
    },
    {
      title: "Cookies and Tracking",
      content: [
        "Essential cookies for platform functionality",
        "Analytics cookies to improve user experience",
        "Marketing cookies for personalized content",
        "Cookie preferences can be managed in your account settings"
      ]
    }
  ];

  const privacyDetails = [
    {
      title: "Data Security",
      content: "We employ bank-level security measures including end-to-end encryption, multi-factor authentication, and regular security audits to protect your information."
    },
    {
      title: "Data Sharing",
      content: "We do not sell your personal information. We may share data only with your consent, for legal compliance, or with trusted service providers under strict confidentiality agreements."
    },
    {
      title: "International Data Transfers",
      content: "As a global platform, your data may be processed in different countries. We ensure all transfers comply with international data protection standards."
    },
    {
      title: "Data Retention",
      content: "We retain your information only as long as necessary for the purposes outlined in this policy, or as required by law. You can request data deletion at any time."
    },
    {
      title: "Children's Privacy",
      content: "Our services are not intended for individuals under 18. We do not knowingly collect personal information from children under 18."
    },
    {
      title: "Policy Updates",
      content: "We may update this privacy policy periodically. Significant changes will be communicated to you via email or platform notifications."
    }
  ];

  return (
    <div className="privacy-page">
      <Header />

      {/* Hero Section */}
      <section className="privacy-hero">
        <div className="container">
          <div className="hero-content">
            <h1>Privacy Policy</h1>
            <p>Your privacy and data security are our top priorities</p>
            <div className="hero-stats">
              <div className="stat">

                <span>Bank-Level Security</span>
              </div>
              <div className="stat">

                <span>End-to-End Encryption</span>
              </div>
              <div className="stat">

                <span>Global Compliance</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Overview Section */}
      <section className="privacy-overview">
        <div className="container">
          <div className="overview-content">
            <h2>Privacy Overview</h2>
            <p>At Ledgora, we are committed to protecting your privacy and ensuring the security
              of your personal and financial information. This privacy policy explains how we collect,
              use, and safeguard your data when you use our platform.
            </p>
            <p>We comply with global privacy regulations including GDPR, CCPA, and other applicable
              data protection laws. Your trust is essential to our relationship, and we are dedicated
              to maintaining the highest standards of data protection.
            </p>
            <div className="overview-highlights">
              <div className="highlight">

                <span>GDPR Compliant</span>
              </div>
              <div className="highlight">

                <span>CCPA Compliant</span>
              </div>
              <div className="highlight">

                <span>SOC 2 Certified</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Sections */}
      <section className="privacy-sections">
        <div className="container">
          <h2>Key Privacy Areas</h2>
          <div className="sections-grid">
            {sections.map((section, index) => (
              <div key={index} className="privacy-section-card">
                <div className="section-icon">
                  {section.icon}
                </div>
                <h3>{section.title}</h3>
                <ul>
                  {section.content.map((item, itemIndex) => (
                    <li key={itemIndex}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Detailed Information */}
      <section className="privacy-details">
        <div className="container">
          <h2>Detailed Privacy Information</h2>
          <div className="details-grid">
            {privacyDetails.map((detail, index) => (
              <div key={index} className="detail-card">
                <h3>{detail.title}</h3>
                <p>{detail.content}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="privacy-contact">
        <div className="container">
          <h2>Privacy Questions?</h2>
          <div className="contact-content">
            <div className="contact-text">
              <p>If you have any questions about our privacy practices or would like to exercise
                your data rights, please don't hesitate to contact us. Our privacy team is here
                to help.
              </p>
              <div className="contact-methods">
                <div className="contact-method">
                  <h4>Data Protection Officer</h4>
                  <p>privacy@ledgora.com</p>
                </div>
                <div className="contact-method">
                  <h4>General Privacy Inquiries</h4>
                  <p>support@ledgora.com</p>
                </div>
              </div>
            </div>
            <div className="contact-actions">
              <Link to="/contact" className="btn-primary">Contact Privacy Team</Link>
              <Link to="/help-center" className="btn-outline">Privacy FAQ</Link>
            </div>
          </div>
        </div>
      </section>

      {/* Compliance Section */}
      <section className="compliance-section">
        <div className="container">
          <h2>Regulatory Compliance</h2>
          <div className="compliance-content">
            <p>Ledgora maintains compliance with major global privacy and data protection regulations:
            </p>
            <div className="compliance-grid">
              <div className="compliance-item">
                <h4>GDPR</h4>
                <p>General Data Protection Regulation (EU)</p>
              </div>
              <div className="compliance-item">
                <h4>CCPA</h4>
                <p>California Consumer Privacy Act (US)</p>
              </div>
              <div className="compliance-item">
                <h4>PIPEDA</h4>
                <p>Personal Information Protection and Electronic Documents Act (Canada)</p>
              </div>
              <div className="compliance-item">
                <h4>PDPA</h4>
                <p>Personal Data Protection Act (Singapore)</p>
              </div>
              <div className="compliance-item">
                <h4>LGPD</h4>
                <p>Lei Geral de Proteção de Dados (Brazil)</p>
              </div>
              <div className="compliance-item">
                <h4>APPI</h4>
                <p>Act on the Protection of Personal Information (Japan)</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Last Updated */}
      <section className="last-updated">
        <div className="container">
          <p>Last updated: December 2024</p>
          <p>This privacy policy was last reviewed and updated on December 1, 2024.</p>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Privacy;