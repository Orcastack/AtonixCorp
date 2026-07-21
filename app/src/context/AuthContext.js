import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { getApiOrigin } from '../utils/apiBaseUrl';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const API_BASE_URL = getApiOrigin();

  const apiUrl = useCallback(
    (path) => {
      if (!path) return API_BASE_URL;
      if (path.startsWith('http://') || path.startsWith('https://')) return path;
      return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
    },
    [API_BASE_URL]
  );

  const buildAuthHeaders = useCallback(() => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const parseApiError = useCallback(async (response, fallbackMessage) => {
    try {
      const data = await response.json();
      if (typeof data?.detail === 'string' && data.detail) {
        return data.detail;
      }
      if (typeof data?.error?.message === 'string' && data.error.message) {
        return data.error.message;
      }
      if (data?.error?.details && typeof data.error.details === 'object') {
        const detailMessage = Object.entries(data.error.details)
          .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(', ') : value}`)
          .join(' | ');
        if (detailMessage) {
          return detailMessage;
        }
      }
      if (data && typeof data === 'object') {
        const flatMessage = Object.entries(data)
          .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(', ') : value}`)
          .join(' | ');
        if (flatMessage) {
          return flatMessage;
        }
      }
    } catch {
      // ignore parse failures and fall back below
    }
    return fallbackMessage;
  }, []);

  const normalizeUser = useCallback((source) => ({
    id: source?.id,
    secure_user_id: source?.secure_user_id || '',
    name: source?.username || source?.email?.split('@')[0] || 'User',
    email: source?.email || '',
    avatar: (source?.username || source?.email || 'U').charAt(0).toUpperCase(),
    account_type: source?.account_type || 'enterprise',
    country: source?.country || '',
    phone: source?.phone || '',
    email_verified: Boolean(source?.email_verified),
  }), []);

  useEffect(() => {
    const initialize = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(apiUrl('/api/auth/me/'), {
          headers: {
            ...buildAuthHeaders(),
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to load user');
        }

        const me = await response.json();
        const derivedUser = normalizeUser(me);

        setUser(derivedUser);
        setIsAuthenticated(true);
        localStorage.setItem('user', JSON.stringify(derivedUser));
      } catch (error) {
        console.error('Auth initialize error:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    initialize();
  }, [apiUrl, buildAuthHeaders, normalizeUser]);

  const login = useCallback(async (identifier, password) => {
    try {
      const tokenRes = await fetch(apiUrl('/api/auth/token/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: identifier, password }),
      });

      if (!tokenRes.ok) {
        const details = await parseApiError(tokenRes, 'Invalid credentials');
        return {
          success: false,
          error: details,
          verificationRequired: details.toLowerCase().includes('verify your email first'),
        };
      }

      const tokenData = await tokenRes.json();
      localStorage.setItem('token', tokenData.access);
      localStorage.setItem('refreshToken', tokenData.refresh);

      const meRes = await fetch(apiUrl('/api/auth/me/'), {
        headers: {
          ...buildAuthHeaders(),
          'Content-Type': 'application/json',
        },
      });

      if (!meRes.ok) {
        return { success: false, error: 'Failed to load user profile' };
      }

      const me = await meRes.json();
      const derivedUser = normalizeUser(tokenData.user || me);

      setUser(derivedUser);
      setIsAuthenticated(true);
      localStorage.setItem('user', JSON.stringify(derivedUser));
      return { success: true, user: derivedUser };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Login failed' };
    }
  }, [apiUrl, buildAuthHeaders, normalizeUser, parseApiError]);

  const register = useCallback(async (username, email, password, country, phone, account_type) => {
    try {
      const response = await fetch(apiUrl('/api/auth/register/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          email,
          password,
          account_type,
          country,
          phone,
        }),
      });

      if (!response.ok) {
        const details = await parseApiError(response, 'Registration failed');
        return {
          success: false,
          error: details,
          verificationRequired: response.status === 409,
        };
      }

      const data = await response.json();
      return { success: true, verificationRequired: Boolean(data.verification_required), user: data.user };
    } catch (error) {
      console.error('Register error:', error);
      return { success: false, error: 'Registration failed' };
    }
  }, [apiUrl, parseApiError]);

  const completeEmailVerification = useCallback(async (token) => {
    try {
      const response = await fetch(apiUrl(`/api/auth/verify-email/?token=${encodeURIComponent(token)}`));
      if (!response.ok) {
        return { success: false, error: await parseApiError(response, 'Unable to verify this email link.') };
      }
      const data = await response.json();
      localStorage.setItem('token', data.access);
      localStorage.setItem('refreshToken', data.refresh);
      const verifiedUser = normalizeUser(data.user);
      setUser(verifiedUser);
      setIsAuthenticated(true);
      localStorage.setItem('user', JSON.stringify(verifiedUser));
      return { success: true, nextPath: data.next_path || '/app/verification' };
    } catch (error) {
      console.error('Email verification error:', error);
      return { success: false, error: 'Unable to verify this email link.' };
    }
  }, [apiUrl, normalizeUser, parseApiError]);

  const resendEmailVerification = useCallback(async (email) => {
    try {
      const response = await fetch(apiUrl('/api/auth/resend-verification/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) {
        return { success: false, error: await parseApiError(response, 'Unable to request a verification email.') };
      }
      return { success: true };
    } catch (error) {
      console.error('Resend verification error:', error);
      return { success: false, error: 'Unable to request a verification email.' };
    }
  }, [apiUrl, parseApiError]);

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    completeEmailVerification,
    resendEmailVerification,
    logout
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
