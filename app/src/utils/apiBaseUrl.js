const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const LOCAL_API_ORIGIN = 'http://localhost:8000';
const PRODUCTION_API_ORIGIN = 'https://api.atonixcorp.com';

const isLocalBrowser = () => typeof window !== 'undefined'
  && LOCAL_HOSTS.has(window.location.hostname);

const configuredApiOrigin = () => {
  const configuredUrl = process.env.REACT_APP_API_URL || process.env.REACT_APP_API_BASE_URL;
  if (!configuredUrl) return '';

  const normalizedOrigin = configuredUrl.replace(/\/api\/?$/, '').replace(/\/$/, '');
  if (isLocalBrowser()) {
    return normalizedOrigin.includes('localhost') || normalizedOrigin.includes('127.0.0.1')
      ? normalizedOrigin
      : LOCAL_API_ORIGIN;
  }

  if (normalizedOrigin.includes('localhost')) return '';
  return normalizedOrigin;
};

export const getApiOrigin = () => configuredApiOrigin()
  || (isLocalBrowser() ? LOCAL_API_ORIGIN : PRODUCTION_API_ORIGIN);

export const getApiBaseUrl = () => `${getApiOrigin()}/api`;