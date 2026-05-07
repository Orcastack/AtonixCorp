import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { organizationsAPI, entitiesAPI, Organization, Entity } from '../services/api';
import { useAuth } from './AuthContext';
import { Storage } from '../services/storage';

interface EnterpriseContextValue {
  currentOrganization: Organization | null;
  organizations: Organization[];
  entities: Entity[];
  loading: boolean;
  error: string;
  fetchOrganizations: () => Promise<void>;
  fetchEntities: (orgId?: number) => Promise<void>;
  switchOrganization: (org: Organization) => void;
}

const EnterpriseContext = createContext<EnterpriseContextValue | undefined>(undefined);

export const EnterpriseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { activeOrg, setActiveOrg } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchOrganizations = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const orgs = await organizationsAPI.getMyOrganizations();
      setOrganizations(Array.isArray(orgs) ? orgs : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEntities = useCallback(async (orgId?: number) => {
    setLoading(true);
    setError('');
    try {
      const res = await entitiesAPI.getAll(orgId) as { results?: Entity[] } | Entity[];
      const list = Array.isArray(res) ? res : (res as { results?: Entity[] }).results ?? [];
      setEntities(list);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load entities');
    } finally {
      setLoading(false);
    }
  }, []);

  const switchOrganization = useCallback(
    (org: Organization) => {
      setActiveOrg(org);
      Storage.setJSON(Storage.keys.ACTIVE_ORG, org);
      fetchEntities(org.id);
    },
    [setActiveOrg, fetchEntities],
  );

  useEffect(() => {
    if (activeOrg) {
      fetchEntities(activeOrg.id);
    }
  }, [activeOrg, fetchEntities]);

  return (
    <EnterpriseContext.Provider
      value={{
        currentOrganization: activeOrg,
        organizations,
        entities,
        loading,
        error,
        fetchOrganizations,
        fetchEntities,
        switchOrganization,
      }}
    >
      {children}
    </EnterpriseContext.Provider>
  );
};

export const useEnterprise = (): EnterpriseContextValue => {
  const ctx = useContext(EnterpriseContext);
  if (!ctx) throw new Error('useEnterprise must be used within EnterpriseProvider');
  return ctx;
};
