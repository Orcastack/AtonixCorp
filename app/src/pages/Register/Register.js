import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { countryDropdownOptions } from '../../utils/countryDropdowns';
import LedgoraLogo from '../../components/branding/LedgoraLogo';

const Register = () => {
  const [step, setStep] = useState(1); // 1: email → 2: details
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [country, setCountry] = useState('US');
  const [phone, setPhone] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState('');
  const { register } = useAuth();
  const navigate = useNavigate();

  const selectedCountry = countryDropdownOptions.find(c => c.code === country);

  // Step 1: Email validation
  const handleEmailSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!email) {
      setError('Please enter your email');
      return;
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email');
      return;
    }

    setStep(2);
  };

  // Step 2: Details submission
  const handleDetailsSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!name || !password || !confirmPassword || !country || !phone || !orgName) {
      setError('Please fill in all fields');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (phone.length < 6) {
      setError('Please enter a valid phone number');
      return;
    }

    const result = await register(name, email, password, country, phone, 'enterprise', orgName);
    if (result.success) {
      navigate('/app/console');
    } else {
      setError(result.error || 'Registration failed. Please try again.');
    }
  };

  // Step 1: Email Entry
  if (step === 1) {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <div className="auth-header">
            <Link to="/" className="auth-logo-link">
              <LedgoraLogo size="medium" withText />
            </Link>
          </div>

          <div className="auth-card">
            <div className="step-indicator">
              <div className="step-dot active"></div>
              <div className="step-dot"></div>
            </div>

            <h1>Create Enterprise Account</h1>
            <p className="auth-subtitle">Step 1 of 2 - Enter your business email</p>

            {error && <div className="auth-error">{error}</div>}

            <form onSubmit={handleEmailSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="email">Business Email Address</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@yourcompany.com"
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <button type="submit" className="btn-primary btn-full">Continue →
              </button>
            </form>

            <div className="auth-footer">
              <p>Already have an account? <Link to="/login">Sign in</Link></p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Details Entry
  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <Link to="/" className="auth-logo-link">
            <LedgoraLogo size="medium" withText />
          </Link>
        </div>

        <div className="auth-card">
          <div className="step-indicator">
            <div className="step-dot completed"></div>
            <div className="step-dot active"></div>
          </div>

          <h1>Complete Your Profile</h1>
          <p className="auth-subtitle">Step 2 of 2 - Enterprise Account</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleDetailsSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                autoComplete="name"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="orgName">Organization Name</label>
              <input
                type="text"
                id="orgName"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Your Company Name"
              />
            </div>

            <div className="form-group">
              <label htmlFor="country">Country</label>
              <select
                id="country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="country-select"
              >
                {countryDropdownOptions.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.flag ? `${c.flag} ` : ''}{c.name}{c.dialCode ? ` (${c.dialCode})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="phone">Phone Number</label>
              <div className="phone-input-wrapper">
                <div className="phone-prefix">
                  <span className="country-flag">{selectedCountry?.flag}</span>
                  <span className="dial-code">{selectedCountry?.dialCode}</span>
                </div>
                <input
                  type="tel"
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value.replace(/[^0-9]/g, ''))}
                  placeholder="123456789"
                  autoComplete="tel"
                  className="phone-input"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <div className="password-input-wrapper">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <button type="submit" className="btn-primary btn-full">Create Account →
            </button>
          </form>

          <button
            type="button"
            className="btn-link"
            onClick={() => {
              setStep(1);
              setError('');
            }}
          >
            ← Back to email
          </button>

          <div className="auth-footer">
            <p>Already have an account? <Link to="/login">Sign in</Link></p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
