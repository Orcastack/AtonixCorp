import React, { useState } from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './HelpCenter.css';

const HelpCenter = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedFaq, setExpandedFaq] = useState(null);

  const faqs = [
    {
      question: "How do I create an account?",
      answer: "To create an account, click the 'Get Started' button on our homepage and follow the registration process. You'll need to provide your email address, create a password, and verify your identity for security purposes."
    },
    {
      question: "What fees do you charge?",
      answer: "We offer transparent pricing with no hidden fees. Personal accounts start at $9.99/month, Professional at $29.99/month, and Enterprise at $99.99/month. All plans include basic transaction fees which vary by asset type."
    },
    {
      question: "How secure is my data?",
      answer: "Security is our top priority. We use bank-level encryption, multi-factor authentication, and comply with global financial regulations. Your data is protected by advanced security measures and regular audits."
    },
    {
      question: "Can I withdraw my funds anytime?",
      answer: "Yes, you can withdraw your funds at any time. Processing times vary by withdrawal method and amount, typically taking 1-5 business days. Enterprise clients may have priority processing."
    },
    {
      question: "Do you support international users?",
      answer: "Absolutely! We support users in 207 countries worldwide. Our platform handles multiple currencies and complies with international financial regulations."
    },
    {
      question: "What cryptocurrencies do you support?",
      answer: "We support major cryptocurrencies including Bitcoin, Ethereum, and many altcoins. Our platform also offers traditional stock and bond trading capabilities."
    }
  ];

  const categories = [
    {
      title: "Getting Started",
      articles: [
        "Creating Your Account",
        "Setting Up Security",
        "Making Your First Investment",
        "Understanding the Dashboard"
      ]
    },
    {
      title: "Trading & Investing",
      articles: [
        "How to Place Orders",
        "Understanding Order Types",
        "Portfolio Management",
        "Risk Management Tools"
      ]
    },
    {
      title: "Account Management",
      articles: [
        "Updating Personal Information",
        "Payment Methods",
        "Transaction History",
        "Account Verification"
      ]
    },
    {
      title: "Security & Privacy",
      articles: [
        "Two-Factor Authentication",
        "Password Security",
        "Privacy Settings",
        "Data Protection"
      ]
    }
  ];

  const tutorials = [
    {
      title: "Platform Overview",
      duration: "5 min",
      description: "Get familiar with the Ledgora platform interface and key features."
    },
    {
      title: "Portfolio Analysis",
      duration: "8 min",
      description: "Learn how to analyze your portfolio performance and make informed decisions."
    },
    {
      title: "Advanced Trading Strategies",
      duration: "12 min",
      description: "Discover advanced trading techniques and risk management strategies."
    },
    {
      title: "Mobile App Guide",
      duration: "6 min",
      description: "Master the Ledgora mobile app for trading on the go."
    }
  ];

  const toggleFaq = (index) => {
    setExpandedFaq(expandedFaq === index ? null : index);
  };

  return (
    <div className="help-center-page">
      <Header />

      {/* Hero Section */}
      <section className="help-hero">
        <div className="container">
          <div className="hero-content">
            <h1>Help Center</h1>
            <p>Find answers, guides, and tutorials to make the most of Ledgora</p>
            <div className="search-box">

              <input
                type="text"
                placeholder="Search for help articles, guides, or FAQs..."
                className="search-input"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Quick Links */}
      <section className="quick-links">
        <div className="container">
          <div className="links-grid">
            <Link to="#faqs" className="quick-link">

              <span>FAQs</span>
            </Link>
            <Link to="#guides" className="quick-link">

              <span>Guides</span>
            </Link>
            <Link to="#videos" className="quick-link">

              <span>Videos</span>
            </Link>
            <Link to="#contact" className="quick-link">

              <span>Contact Support</span>
            </Link>
          </div>
        </div>
      </section>

      {/* FAQs Section */}
      <section id="faqs" className="faqs-section">
        <div className="container">
          <h2>Frequently Asked Questions</h2>
          <div className="faqs-list">
            {faqs.map((faq, index) => (
              <div key={index} className="faq-item">
                <button
                  className="faq-question"
                  onClick={() => toggleFaq(index)}
                >
                  <span>{faq.question}</span>

                </button>
                {expandedFaq === index && (
                  <div className="faq-answer">
                    <p>{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section id="guides" className="categories-section">
        <div className="container">
          <h2>Help Articles by Category</h2>
          <div className="categories-grid">
            {categories.map((category, index) => (
              <div key={index} className="category-card">
                <div className="category-header">
                  <div className="category-icon">
                    {category.icon}
                  </div>
                  <h3>{category.title}</h3>
                </div>
                <ul className="article-list">
                  {category.articles.map((article, articleIndex) => (
                    <li key={articleIndex}>
                      <Link to={`/help/${article.toLowerCase().replace(/\s+/g, '-')}`}>
                        {article}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Video Tutorials */}
      <section id="videos" className="tutorials-section">
        <div className="container">
          <h2>Video Tutorials</h2>
          <div className="tutorials-grid">
            {tutorials.map((tutorial, index) => (
              <div key={index} className="tutorial-card">
                <div className="tutorial-thumbnail">

                  <span className="duration">{tutorial.duration}</span>
                </div>
                <div className="tutorial-content">
                  <h3>{tutorial.title}</h3>
                  <p>{tutorial.description}</p>
                  <button className="watch-btn">
                    Watch Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="contact-section">
        <div className="container">
          <h2>Still Need Help?</h2>
          <div className="contact-content">
            <div className="contact-text">
              <p>Can't find what you're looking for? Our support team is here to help.
                Contact us through any of the channels below.
              </p>
              <div className="contact-options">
                <div className="contact-option">
                  <h4>Live Chat</h4>
                  <p>Get instant help during business hours</p>
                  <button className="contact-btn">Start Chat</button>
                </div>
                <div className="contact-option">
                  <h4>Email Support</h4>
                  <p>Send us a detailed message</p>
                  <a href="mailto:support@ledgora.com" className="contact-btn">Email Us</a>
                </div>
                <div className="contact-option">
                  <h4>Phone Support</h4>
                  <p>Speak directly with our experts</p>
                  <a href="tel:+15551234567" className="contact-btn">Call Now</a>
                </div>
              </div>
            </div>
            <div className="contact-image">
              <div className="image-placeholder">

                <span>24/7 Support</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default HelpCenter;