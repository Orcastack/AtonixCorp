import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { authAPI, organizationsAPI, Organization } from '../services/api';
import { Storage } from '../services/storage';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AppUser {
  id: number;
  name: string;
  email: string;
  avatar: string;
  account_type: string;
  country: string;
  phone: string;
}

interface AuthState {
  user: AppUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  activeOrg: Organization | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  loginWithCompanyId: (companySlug: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  setActiveOrg: (org: Organization) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    loading: true,
    activeOrg: null,
  });

  // ── Hydrate on mount ──────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const token = await Storage.get(Storage.keys.TOKEN);
      if (!token) {
        setState(s => ({ ...s, loading: false }));
        return;
      }
      try {
        const me = await authAPI.me();
        const user = deriveUser(me);
        const activeOrg = await Storage.getJSON<Organization>(Storage.keys.ACTIVE_ORG);
        setState({ user, isAuthenticated: true, loading: false, activeOrg: activeOrg ?? null });
      } catch {
        await clearAuthStorage();
        setState({ user: null, isAuthenticated: false, loading: false, activeOrg: null });
      }
    })();
  }, []);

  // ── Standard login (email + password) ────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    try {
      const tokens = await authAPI.token(email, password);
      await Storage.set(Storage.keys.TOKEN, tokens.access);
      await Storage.set(Storage.keys.REFRESH_TOKEN, tokens.refresh);

      const me = await authAPI.me();
      const user = deriveUser(me);
      await Storage.setJSON(Storage.keys.USER, user);

      setState(s => ({ ...s, user, isAuthenticated: true }));
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: errorMessage(err) };
    }
  }, []);

  // ── Company-ID login (slug → verify org → then authenticate) ─────────────
  // Flow:
  //   1. Authenticate the user with email + password (same /auth/token/ endpoint)
  //   2. Look up their organizations and verify the companySlug matches one of them
  //   3. Set that organization as the active org
  //   This keeps the identity layer identical to the platform while scoping
  //   the session to a specific company — no separate login endpoint needed.
  const loginWithCompanyId = useCallback(
    async (companySlug: string, email: string, password: string) => {
      try {
        // Step 1 — authenticate
        const tokens = await authAPI.token(email, password);
        await Storage.set(Storage.keys.TOKEN, tokens.access);
        await Storage.set(Storage.keys.REFRESH_TOKEN, tokens.refresh);

        // Step 2 — load user profile
        const me = await authAPI.me();
        const user = deriveUser(me);
        await Storage.setJSON(Storage.keys.USER, user);

        // Step 3 — find the org by slug
        const orgs = await organizationsAPI.getMyOrganizations();
        const normalised = companySlug.trim().toLowerCase();
        const matchedOrg = orgs.find(
          o =>
            (o.slug ?? '').toLowerCase() === normalised ||
            o.name.toLowerCase().replace(/\s+/g, '-') === normalised,
        );

        if (!matchedOrg) {
          // Company ID not found in user's orgs — revoke tokens
          await clearAuthStorage();
          return {
            success: false,
            error: 'Company ID not found or you do not have access to this company.',
          };
        }

        await Storage.setJSON(Storage.keys.ACTIVE_ORG, matchedOrg);
        setState({ user, isAuthenticated: true, loading: false, activeOrg: matchedOrg });
        return { success: true };
      } catch (err: unknown) {
        await clearAuthStorage();
        return { success: false, error: errorMessage(err) };
      }
    },
    [],
  );

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    await clearAuthStorage();
    setState({ user: null, isAuthenticated: false, loading: false, activeOrg: null });
  }, []);

  const setActiveOrg = useCallback((org: Organization) => {
    Storage.setJSON(Storage.keys.ACTIVE_ORG, org);
    setState(s => ({ ...s, activeOrg: org }));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, loginWithCompanyId, logout, setActiveOrg }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function deriveUser(me: { id: number; username: string; email: string; account_type: string; country: string; phone: string }): AppUser {
  return {
    id: me.id,
    name: me.username || me.email?.split('@')[0] || 'User',
    email: me.email,
    avatar: (me.username || me.email || 'U').charAt(0).toUpperCase(),
    account_type: me.account_type || 'enterprise',
    country: me.country || '',
    phone: me.phone || '',
  };
}

async function clearAuthStorage() {
  await Storage.remove(Storage.keys.TOKEN);
  await Storage.remove(Storage.keys.REFRESH_TOKEN);
  await Storage.remove(Storage.keys.USER);
  await Storage.remove(Storage.keys.ACTIVE_ORG);
}

function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred';
}
