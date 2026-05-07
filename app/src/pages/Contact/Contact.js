import React, { useState } from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';

const Contact = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Handle form submission here
    console.log('Form submitted:', formData);
    // Reset form
    setFormData({
      name: '',
      email: '',
      subject: '',
      message: ''
    });
    alert('Thank you for your message! We\'ll get back to you soon.');
  };

  const offices = [
    {
      city: 'New York',
      address: '123 Financial District, New York, NY 10004',
      phone: '+1 (555) 123-4567',
      email: 'ny@ledgora.com'
    },
    {
      city: 'London',
      address: '45 Cannon Street, London EC4N 5AE, UK',
      phone: '+44 20 7123 4567',
      email: 'london@ledgora.com'
    },
    {
      city: 'Singapore',
      address: '1 Raffles Place, #20-01, Singapore 048616',
      phone: '+65 6789 0123',
      email: 'singapore@ledgora.com'
    }
  ];

  const contactMethods = [
    {
      title: 'Phone Support',
      description: 'Speak directly with our experts',
      contact: '+1 (555) 123-4567',
      availability: 'Mon-Fri, 9AM-6PM EST'
    },
    {
      title: 'Email Support',
      description: 'Send us a detailed message',
      contact: 'support@ledgora.com',
      availability: '24/7 Response within 24 hours'
    },
    {
      title: 'Live Chat',
      description: 'Get instant help online',
      contact: 'Available on our website',
      availability: 'Mon-Fri, 9AM-6PM EST'
    }
  ];

  return (
    <div className="contact-page">
      <Header />

      {/* Hero Section */}
      <section className="contact-hero">
        <div className="container">
          <div className="hero-content">
            <h1>Contact Us</h1>
            <p>Get in touch with our team. We're here to help you succeed.</p>
          </div>
        </div>
      </section>

      {/* Contact Form Section */}
      <section className="contact-form-section">
        <div className="container">
          <div className="contact-content">
            <div className="contact-info">
              <h2>Get In Touch</h2>
              <p>Have questions about our platform, need support, or want to learn more about
                our services? We'd love to hear from you. Send us a message and we'll respond
                as soon as possible.
              </p>

              <div className="contact-methods">
                {contactMethods.map((method, index) => (
                  <div key={index} className="contact-method">
                    <div className="method-icon">
                      {method.icon}
                    </div>
                    <div className="method-content">
                      <h3>{method.title}</h3>
                      <p>{method.description}</p>
                      <div className="method-contact">{method.contact}</div>
                      <div className="method-availability">{method.availability}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="contact-form">
              <h2>Send us a Message</h2>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="name">Full Name</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    placeholder="Your full name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                    placeholder="your.email@example.com"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="subject">Subject</label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleInputChange}
                    required
                    placeholder="How can we help you?"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="message">Message</label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleInputChange}
                    required
                    placeholder="Tell us more about your inquiry..."
                    rows="6"
                  ></textarea>
                </div>

                <button type="submit" className="submit-btn">
                  Send Message
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* Offices Section */}
      <section className="offices-section">
        <div className="container">
          <h2>Our Offices</h2>
          <div className="offices-grid">
            {offices.map((office, index) => (
              <div key={index} className="office-card">
                <div className="office-header">

                  <h3>{office.city}</h3>
                </div>
                <div className="office-details">
                  <p className="office-address">{office.address}</p>
                  <div className="office-contact">
                    <div className="contact-item">

                      <span>{office.phone}</span>
                    </div>
                    <div className="contact-item">

                      <span>{office.email}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Business Hours Section */}
      <section className="hours-section">
        <div className="container">
          <div className="hours-content">
            <div className="hours-info">

              <div>
                <h3>Business Hours</h3>
                <div className="hours-schedule">
                  <div className="schedule-item">
                    <span className="day">Monday - Friday</span>
                    <span className="time">9:00 AM - 6:00 PM EST</span>
                  </div>
                  <div className="schedule-item">
                    <span className="day">Saturday</span>
                    <span className="time">10:00 AM - 4:00 PM EST</span>
                  </div>
                  <div className="schedule-item">
                    <span className="day">Sunday</span>
                    <span className="time">Closed</span>
                  </div>
                </div>
                <p className="hours-note">Emergency support available 24/7 for Enterprise clients.
                </p>
              </div>
            </div>
            <div className="hours-cta">
              <h3>Need Immediate Help?</h3>
              <p>Our support team is ready to assist you with any urgent matters.</p>
              <div className="cta-buttons">
                <Link to="/support" className="btn-primary">Live Support</Link>
                <a href="tel:+15551234567" className="btn-outline">Call Now</a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Map Section */}
      <section className="map-section">
        <div className="container">
          <div className="map-placeholder">

            <h3>Global Presence</h3>
            <p>Serving clients in 207 countries worldwide</p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Contact;