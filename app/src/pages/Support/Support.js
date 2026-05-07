import React, { useState } from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './Support.css';

const Support = () => {
  const [showTicketModal, setShowTicketModal] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [ticketForm, setTicketForm] = useState({
    name: '',
    email: '',
    subject: '',
    category: 'general',
    priority: 'medium',
    description: ''
  });
  const [chatMessages, setChatMessages] = useState([
    { sender: 'bot', text: 'Hello! How can I help you today?', time: new Date().toLocaleTimeString() }
  ]);
  const [chatInput, setChatInput] = useState('');

  const handleTicketSubmit = (e) => {
    e.preventDefault();
    // Here you would typically send the ticket data to your backend
    console.log('Ticket submitted:', ticketForm);
    alert('Your support ticket has been submitted successfully! We will get back to you within 24 hours.');
    setShowTicketModal(false);
    setTicketForm({
      name: '',
      email: '',
      subject: '',
      category: 'general',
      priority: 'medium',
      description: ''
    });
  };

  const handleChatSend = () => {
    if (chatInput.trim()) {
      const newMessage = {
        sender: 'user',
        text: chatInput,
        time: new Date().toLocaleTimeString()
      };
      setChatMessages([...chatMessages, newMessage]);
      setChatInput('');

      // Simulate bot response
      setTimeout(() => {
        const botResponse = {
          sender: 'bot',
          text: 'Thank you for your message. A support agent will be with you shortly.',
          time: new Date().toLocaleTimeString()
        };
        setChatMessages(prev => [...prev, botResponse]);
      }, 1000);
    }
  };

  return (
    <div className="support-page">
      <Header />

      {/* Hero Section */}
      <section className="support-hero">
        <div className="container">
          <div className="hero-content">
            <h1>Support Center</h1>
            <p>Get the help you need, when you need it</p>
            <div className="search-box">
              <input
                type="text"
                placeholder="Search for help articles, guides, or FAQs..."
                className="search-input"
              />
              <button className="search-btn">Search</button>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Help Section */}
      <section className="quick-help">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Quick Help</h2>
            <p className="section-subtitle">Find the answers you need instantly with our self-service resources</p>
          </div>
          <div className="help-grid">
            <div className="help-card">
              <div className="help-icon">

              </div>
              <h3>FAQs</h3>
              <p>Find answers to commonly asked questions about our platform and services.</p>
              <Link to="/help-center" className="help-link">Browse FAQs</Link>
            </div>
            <div className="help-card">
              <div className="help-icon">

              </div>
              <h3>Documentation</h3>
              <p>Comprehensive guides and tutorials to help you make the most of Ledgora.</p>
              <Link to="/help-center" className="help-link">View Docs</Link>
            </div>
            <div className="help-card">
              <div className="help-icon">

              </div>
              <h3>Video Tutorials</h3>
              <p>Step-by-step video guides to walk you through our key features and tools.</p>
              <Link to="/help-center" className="help-link">Watch Videos</Link>
            </div>
            <div className="help-card">
              <div className="help-icon">

              </div>
              <h3>Live Support</h3>
              <p>Connect with our support team for personalized assistance.</p>
              <Link to="#contact-support" className="help-link">Get Support</Link>
            </div>
          </div>
        </div>
      </section>

      {/* Popular Topics */}
      <section className="popular-topics">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Popular Topics</h2>
            <p className="section-subtitle">Explore our most frequently accessed help articles and guides</p>
          </div>
          <div className="topics-grid">
            <div className="topic-category">
              <h3>Getting Started</h3>
              <ul>
                <li><Link to="/help-center">Creating your account</Link></li>
                <li><Link to="/help-center">Setting up your profile</Link></li>
                <li><Link to="/help-center">First investment guide</Link></li>
                <li><Link to="/help-center">Security best practices</Link></li>
              </ul>
            </div>
            <div className="topic-category">
              <h3>Account Management</h3>
              <ul>
                <li><Link to="/help-center">Managing your portfolio</Link></li>
                <li><Link to="/help-center">Transaction history</Link></li>
                <li><Link to="/help-center">Updating payment methods</Link></li>
                <li><Link to="/help-center">Account verification</Link></li>
              </ul>
            </div>
            <div className="topic-category">
              <h3>Trading & Investing</h3>
              <ul>
                <li><Link to="/help-center">Placing orders</Link></li>
                <li><Link to="/help-center">Understanding fees</Link></li>
                <li><Link to="/help-center">Market analysis tools</Link></li>
                <li><Link to="/help-center">Risk management</Link></li>
              </ul>
            </div>
            <div className="topic-category">
              <h3>Enterprise Features</h3>
              <ul>
                <li><Link to="/help-center">Team management</Link></li>
                <li><Link to="/help-center">API integration</Link></li>
                <li><Link to="/help-center">Custom reporting</Link></li>
                <li><Link to="/help-center">Compliance tools</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Support Section */}
      <section id="contact-support" className="contact-support">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Contact Our Support Team</h2>
            <p className="section-subtitle">Choose the best way to reach us - we're here to help 24/7</p>
          </div>
          <div className="contact-grid">
            <div className="contact-method">
              <div className="contact-icon">

              </div>
              <h3>Live Chat</h3>
              <p>Get instant help from our support team during business hours.</p>
              <div className="contact-info">
                <span>Available: Mon-Fri, 9AM-6PM EST</span>
              </div>
              <button className="contact-btn" onClick={() => setShowChat(true)}>Start Chat</button>
            </div>
            <div className="contact-method">
              <div className="contact-icon">

              </div>
              <h3>Email Support</h3>
              <p>Send us a detailed message and we'll get back to you within 24 hours.</p>
              <div className="contact-info">
                <span>support@ledgora.com</span>
                <span>Response time: 24 hours</span>
              </div>
            </div>
            <div className="contact-method">
              <div className="contact-icon">

              </div>
              <h3>Phone Support</h3>
              <p>Speak directly with our experts for urgent matters.</p>
              <div className="contact-info">
                <span>+1 (555) 123-4567</span>
                <span>Available: Mon-Fri, 9AM-5PM EST</span>
              </div>
            </div>
            <div className="contact-method">
              <div className="contact-icon">

              </div>
              <h3>Submit a Ticket</h3>
              <p>Create a support ticket for complex issues that need detailed investigation.</p>
              <div className="contact-info">
                <span>Priority support for Enterprise clients</span>
              </div>
              <button className="contact-btn" onClick={() => setShowTicketModal(true)}>Submit Ticket</button>
            </div>
          </div>
        </div>
      </section>

      {/* Status Updates */}
      <section className="status-section">
        <div className="container">
          <div className="status-content">
            <div className="status-info">
              <h3>System Status</h3>
              <div className="status-indicator">
                <div className="status-dot operational"></div>
                <span>All Systems Operational</span>
              </div>
              <p>View real-time status updates and maintenance schedules.</p>
            </div>
            <div className="status-links">
              <Link to="/status" className="status-link">View Status Page</Link>
              <Link to="/help-center" className="status-link">Incident History</Link>
            </div>
          </div>
        </div>
      </section>

      {/* Community Section */}
      <section className="community-section">
        <div className="container">
          <div className="section-header">
            <h2 className="section-title">Join Our Community</h2>
            <p className="section-subtitle">Connect with fellow users and share experiences</p>
          </div>
          <div className="community-content">
            <div className="community-text">
              <p>Connect with other Ledgora users, share insights, and learn from the community.
                Our forums and social channels are great places to get peer support and discover new ways
                to maximize your financial potential.
              </p>
              <div className="community-links">
                <a href="https://community.atonixcapital.com" target="_blank" rel="noopener noreferrer" className="community-link">User Forums</a>
                <a href="https://facebook.com/groups/atonixcapital" target="_blank" rel="noopener noreferrer" className="community-link">Facebook Group</a>
                <a href="https://twitter.com/atonixcapital" target="_blank" rel="noopener noreferrer" className="community-link">Twitter</a>
                <a href="https://linkedin.com/company/atonixcapital" target="_blank" rel="noopener noreferrer" className="community-link">LinkedIn</a>
              </div>
            </div>
            <div className="community-stats">
              <div className="stat">
                <div className="stat-number">50K+</div>
                <div className="stat-label">Community Members</div>
              </div>
              <div className="stat">
                <div className="stat-number">10K+</div>
                <div className="stat-label">Daily Discussions</div>
              </div>
              <div className="stat">
                <div className="stat-number">95%</div>
                <div className="stat-label">Questions Answered</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Submit Ticket Modal */}
      {showTicketModal && (
        <div className="modal-overlay" onClick={() => setShowTicketModal(false)}>
          <div className="modal-content ticket-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Submit Support Ticket</h2>
              <button className="modal-close" onClick={() => setShowTicketModal(false)}>

              </button>
            </div>
            <form onSubmit={handleTicketSubmit} className="ticket-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    required
                    value={ticketForm.name}
                    onChange={(e) => setTicketForm({...ticketForm, name: e.target.value})}
                    placeholder="John Doe"
                  />
                </div>
                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    type="email"
                    required
                    value={ticketForm.email}
                    onChange={(e) => setTicketForm({...ticketForm, email: e.target.value})}
                    placeholder="john@example.com"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Subject *</label>
                <input
                  type="text"
                  required
                  value={ticketForm.subject}
                  onChange={(e) => setTicketForm({...ticketForm, subject: e.target.value})}
                  placeholder="Brief description of your issue"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Category *</label>
                  <select
                    value={ticketForm.category}
                    onChange={(e) => setTicketForm({...ticketForm, category: e.target.value})}
                  >
                    <option value="general">General Inquiry</option>
                    <option value="technical">Technical Issue</option>
                    <option value="billing">Billing & Payments</option>
                    <option value="account">Account Management</option>
                    <option value="trading">Trading & Investing</option>
                    <option value="enterprise">Enterprise Support</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Priority *</label>
                  <select
                    value={ticketForm.priority}
                    onChange={(e) => setTicketForm({...ticketForm, priority: e.target.value})}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Description *</label>
                <textarea
                  required
                  rows="6"
                  value={ticketForm.description}
                  onChange={(e) => setTicketForm({...ticketForm, description: e.target.value})}
                  placeholder="Please provide detailed information about your issue..."
                ></textarea>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowTicketModal(false)}>Cancel
                </button>
                <button type="submit" className="btn-submit">Submit Ticket
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Chat Widget */}
      {showChat && (
        <div className="chat-widget">
          <div className="chat-header">
            <div className="chat-header-info">

              <div>
                <h3>Live Support</h3>
                <span className="chat-status">Online</span>
              </div>
            </div>
            <button className="chat-close" onClick={() => setShowChat(false)}>

            </button>
          </div>
          <div className="chat-messages">
            {chatMessages.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender}`}>
                <div className="message-content">
                  <p>{msg.text}</p>
                  <span className="message-time">{msg.time}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="chat-input-area">
            <input
              type="text"
              placeholder="Type your message..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChatSend()}
            />
            <button onClick={handleChatSend} className="chat-send-btn">

            </button>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
};

export default Support;