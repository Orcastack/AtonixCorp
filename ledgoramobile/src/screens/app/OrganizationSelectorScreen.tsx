import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import { organizationsAPI, Organization } from '../../services/api';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

const getInitials = (name = '') =>
  name.split(' ').filter(Boolean).slice(0, 2).map(p => p[0]?.toUpperCase()).join('') || 'LG';

const formatDate = (val?: string) => {
  if (!val) return '';
  try {
    return new Date(val).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch { return val; }
};

const OrgCard: React.FC<{ org: Organization; onOpen: () => void }> = ({ org, onOpen }) => (
  <View style={styles.card}>
    <View style={styles.cardTop}>
      <View style={styles.avatarWrap}>
        <Text style={styles.avatarText}>{getInitials(org.name)}</Text>
      </View>
      <View style={styles.cardHead}>
        <Text style={styles.cardName}>{org.name}</Text>
        <Text style={styles.cardSub} numberOfLines={1}>
          {org.description || org.industry || 'Organization'}
        </Text>
      </View>
      {org.created_at && (
        <Text style={styles.cardBadge}>{formatDate(org.created_at)}</Text>
      )}
    </View>

    <View style={styles.cardFields}>
      {[
        { label: 'Industry', value: org.industry },
        { label: 'Country', value: org.primary_country },
        { label: 'Currency', value: org.primary_currency || 'USD' },
        { label: 'Employees', value: org.employee_count?.toString() },
      ].map(f => f.value ? (
        <View style={styles.cardField} key={f.label}>
          <Text style={styles.cardFieldLabel}>{f.label}</Text>
          <Text style={styles.cardFieldValue}>{f.value}</Text>
        </View>
      ) : null)}
    </View>

    <TouchableOpacity style={styles.openBtn} onPress={onOpen} activeOpacity={0.85}>
      <Text style={styles.openBtnText}>Open Organization</Text>
    </TouchableOpacity>
  </View>
);

const OrganizationSelectorScreen: React.FC<Props> = ({ navigation }) => {
  const { user } = useAuth();
  const { switchOrganization } = useEnterprise();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    try {
      const data = await organizationsAPI.getMyOrganizations();
      setOrgs(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load organizations');
    }
  };

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const handleOpen = (org: Organization) => {
    switchOrganization(org);
    navigation.navigate('OrgOverview');
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.kicker}>Organization Selector</Text>
        <Text style={styles.title}>Choose an organization</Text>
        {user?.name && (
          <Text style={styles.subtitle}>{user.name}, open the organization you want to work in.</Text>
        )}
        <View style={styles.summary}>
          <Text style={styles.summaryText}>
            {orgs.length} {orgs.length === 1 ? 'organization' : 'organizations'} available
          </Text>
        </View>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.createBtn}
          onPress={() => navigation.navigate('CreateOrganization')}
          activeOpacity={0.85}
        >
          <Text style={styles.createBtnText}>+ Create Organization</Text>
        </TouchableOpacity>
      </View>

      {!!error && <Text style={styles.errorText}>{error}</Text>}

      {orgs.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>No organizations yet</Text>
          <Text style={styles.emptyBody}>Create your first organization using the button above.</Text>
        </View>
      ) : (
        <FlatList
          data={orgs}
          keyExtractor={o => String(o.id)}
          renderItem={({ item }) => (
            <OrgCard org={item} onOpen={() => handleOpen(item)} />
          )}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
        />
      )}
    </View>
  );
};

export default OrganizationSelectorScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.xl, paddingBottom: Spacing.md },
  kicker: { fontSize: Typography.fontSizeXs, fontWeight: Typography.fontWeightSemibold, color: Colors.primary, letterSpacing: 1, textTransform: 'uppercase', marginBottom: Spacing.xs },
  title: { fontSize: Typography.fontSizeXxl, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.xs },
  subtitle: { fontSize: Typography.fontSizeSm, color: Colors.text, marginBottom: Spacing.sm },
  summary: { flexDirection: 'row', gap: Spacing.md },
  summaryText: { fontSize: Typography.fontSizeSm, color: Colors.text },
  actions: { paddingHorizontal: Spacing.lg, paddingBottom: Spacing.md, flexDirection: 'row', gap: Spacing.sm },
  createBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: 10,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.md,
  },
  createBtnText: { color: Colors.white, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightSemibold },
  errorText: { color: Colors.error, paddingHorizontal: Spacing.lg, marginBottom: Spacing.sm, fontSize: Typography.fontSizeSm },
  list: { paddingHorizontal: Spacing.lg, paddingBottom: Spacing.xxl },
  card: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: Spacing.md },
  avatarWrap: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    backgroundColor: Colors.muted,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.sm,
  },
  avatarText: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  cardHead: { flex: 1 },
  cardName: { fontSize: Typography.fontSizeMd, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  cardSub: { fontSize: Typography.fontSizeSm, color: Colors.text },
  cardBadge: { fontSize: Typography.fontSizeXs, color: Colors.text },
  cardFields: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, marginBottom: Spacing.md },
  cardField: { minWidth: '45%' },
  cardFieldLabel: { fontSize: Typography.fontSizeXs, color: Colors.text, marginBottom: 2 },
  cardFieldValue: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium, color: Colors.heading },
  openBtn: {
    backgroundColor: Colors.heading,
    borderRadius: Radius.md,
    paddingVertical: 12,
    alignItems: 'center',
  },
  openBtnText: { color: Colors.white, fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.sm },
  emptyBody: { fontSize: Typography.fontSizeSm, color: Colors.text, textAlign: 'center' },
});
