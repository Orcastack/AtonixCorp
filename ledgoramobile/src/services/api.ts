import { Storage } from './storage';

const API_BASE_URL = __DEV__
  ? 'http://10.0.2.2:8000/api'  // Android emulator → host machine localhost
  : 'https://api.ledgora.com/api';

// ---------------------------------------------------------------------------
// Core fetch wrapper with JWT auth + auto-refresh
// ---------------------------------------------------------------------------

async function request<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await Storage.get(Storage.keys.TOKEN);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
  let response = await fetch(url, { ...options, headers });

  // Attempt token refresh once on 401
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const newToken = await Storage.get(Storage.keys.TOKEN);
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(url, { ...options, headers });
    }
  }

  if (!response.ok) {
    let errorMessage = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data?.detail === 'string') errorMessage = data.detail;
      else if (typeof data?.error?.message === 'string') errorMessage = data.error.message;
    } catch {}
    throw new ApiError(errorMessage, response.status);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = await Storage.get(Storage.keys.REFRESH_TOKEN);
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    await Storage.set(Storage.keys.TOKEN, data.access);
    return true;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface MeResponse {
  id: number;
  username: string;
  email: string;
  account_type: string;
  country: string;
  phone: string;
}

export const authAPI = {
  token: (username: string, password: string) =>
    request<TokenResponse>('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<MeResponse>('/auth/me/'),
  register: (data: Record<string, string>) =>
    request<{ access: string; refresh: string; user: MeResponse }>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ---------------------------------------------------------------------------
// Organizations API
// ---------------------------------------------------------------------------
export interface Organization {
  id: number;
  name: string;
  slug: string;
  description?: string;
  industry?: string;
  primary_country?: string;
  primary_currency?: string;
  employee_count?: number;
  email?: string;
  address?: string;
  website?: string;
  service_time?: string;
  logo_url?: string;
  status?: string;
  created_at?: string;
  owner_email?: string;
}

export const organizationsAPI = {
  getMyOrganizations: () =>
    request<Organization[]>('/organizations/my_organizations/'),
  getById: (id: number) =>
    request<Organization>(`/organizations/${id}/`),
  getBySlug: (slug: string) =>
    request<Organization[]>(`/organizations/?slug=${encodeURIComponent(slug)}`),
  getOverview: (id: number) =>
    request(`/organizations/${id}/overview/`),
  create: (data: Record<string, unknown>) =>
    request<Organization>('/organizations/', { method: 'POST', body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// Entities API
// ---------------------------------------------------------------------------
export interface Entity {
  id: number;
  name: string;
  entity_type?: string;
  status?: string;
  country?: string;
  local_currency?: string;
  registration_number?: string;
  main_bank?: string;
  fiscal_year_end?: string;
  next_filing_date?: string;
  created_at?: string;
  organization?: number;
  enabled_modules?: string[];
}

export const entitiesAPI = {
  getAll: (orgId?: number) =>
    request<{ results: Entity[]; count: number }>(
      orgId ? `/entities/?organization=${orgId}` : '/entities/',
    ),
  getById: (id: number) => request<Entity>(`/entities/${id}/`),
  create: (data: Record<string, unknown>) =>
    request<Entity>('/entities/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Record<string, unknown>) =>
    request<Entity>(`/entities/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) =>
    request(`/entities/${id}/`, { method: 'DELETE' }),
};

// ---------------------------------------------------------------------------
// Team Members API
// ---------------------------------------------------------------------------
export interface TeamMember {
  id: number;
  user?: { id: number; username: string; email: string };
  role?: string;
  email?: string;
  joined_at?: string;
}

export const teamMembersAPI = {
  getAll: () => request<TeamMember[]>('/team-members/'),
  create: (data: Record<string, unknown>) =>
    request<TeamMember>('/team-members/', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: number) =>
    request(`/team-members/${id}/`, { method: 'DELETE' }),
};

// ---------------------------------------------------------------------------
// Financial APIs (mirror of platform api.js)
// ---------------------------------------------------------------------------
export const expensesAPI = {
  getAll: () => request('/expenses/'),
  getTotal: () => request('/expenses/total/'),
  getByCategory: () => request('/expenses/by_category/'),
  create: (data: Record<string, unknown>) =>
    request('/expenses/', { method: 'POST', body: JSON.stringify(data) }),
};

export const incomeAPI = {
  getAll: () => request('/income/'),
  getTotal: () => request('/income/total/'),
};

export const budgetsAPI = {
  getAll: () => request('/budgets/'),
  getSummary: () => request('/budgets/summary/'),
};

export const reportsAPI = {
  getAll: () => request('/reports/'),
  generate: (id: number) => request(`/reports/${id}/generate/`, { method: 'POST' }),
};

export const taxAPI = {
  list: () => request('/tax/countries/'),
  get: (code: string) => request(`/tax/countries/${code}/`),
};

export const aiInsightsAPI = {
  getAll: () => request('/ai-insights/'),
  getUnread: () => request('/ai-insights/unread/'),
  markRead: (id: number) => request(`/ai-insights/${id}/mark_read/`, { method: 'POST' }),
};

export default request;
