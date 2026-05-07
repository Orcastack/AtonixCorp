import React, { useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { useEnterprise } from '../../context/EnterpriseContext';
import { useAuth } from '../../context/AuthContext';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

const QUICK_ACTIONS = [
  { key: 'entities', eyebrow: 'Structure', title: 'Business Suite', description: 'Manage entities and legal structure', screen: 'Entities' },
  { key: 'team', eyebrow: 'Access', title: 'Manage Team', description: 'Control access and permissions', screen: 'Team' },
  { key: 'reports', eyebrow: 'Output', title: 'Reports', description: 'Generate consolidated reports', screen: 'Reports' },
  { key: 'compliance', eyebrow: 'Control', title: 'Tax Compliance', description: 'Track deadlines and obligations', screen: 'TaxCompliance' },
];

const FINANCIAL_POSITIONS = [
  { key: 'cash', label: 'Cash & Equivalents', icon: 'CA' },
  { key: 'investments', label: 'Investments', icon: 'IN' },
  { key: 'real-estate', label: 'Real Estate', icon: 'RE' },
  { key: 'crypto', label: 'Cryptocurrency', icon: 'BT' },
];

const OrgOverviewScreen: React.FC<Props> = ({ navigation }) => {
  const { currentOrganization, entities, fetchEntities, loading } = useEnterprise();
  const { logout } = useAuth();

  useEffect(() => {
    if (currentOrganization) {
      fetchEntities(currentOrganization.id);
    }
  }, [currentOrganization]);

  if (!currentOrganization) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No organization selected</Text>
        <TouchableOpacity style={styles.primaryBtn} onPress={() => navigation.navigate('OrgSelector')}>
          <Text style={styles.primaryBtnText}>Select Organization</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const initials = (currentOrganization.name || 'W').slice(0, 2).toUpperCase();
  const entityCount = entities.length;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={loading}
          onRefresh={() => fetchEntities(currentOrganization.id)}
          tintColor={Colors.primary}
        />
      }
    >
      {/* Org Header */}
      <View style={styles.orgHeader}>
        <View style={styles.orgAvatar}>
          <Text style={styles.orgAvatarText}>{initials}</Text>
        </View>
        <View style={styles.orgInfo}>
          <Text style={styles.orgName}>{currentOrganization.name}</Text>
          {currentOrganization.industry && (
            <Text style={styles.orgMeta}>{currentOrganization.industry}</Text>
          )}
          {currentOrganization.primary_country && (
            <Text style={styles.orgMeta}>{currentOrganization.primary_country}</Text>
          )}
        </View>
        <View style={styles.statusBadge}>
          <Text style={styles.statusText}>Active</Text>
        </View>
      </View>

      {/* Stats row */}
      <View style={styles.statsRow}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{entityCount}</Text>
          <Text style={styles.statLabel}>Entities</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{currentOrganization.primary_currency || 'USD'}</Text>
          <Text style={styles.statLabel}>Currency</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{currentOrganization.employee_count ?? '—'}</Text>
          <Text style={styles.statLabel}>Employees</Text>
        </View>
      </View>

      {/* Quick actions */}
      <Text style={styles.sectionTitle}>Quick Actions</Text>
      <View style={styles.actionsGrid}>
        {QUICK_ACTIONS.map(a => (
          <TouchableOpacity
            key={a.key}
            style={styles.actionCard}
            onPress={() => navigation.navigate(a.screen)}
            activeOpacity={0.85}
          >
            <Text style={styles.actionEyebrow}>{a.eyebrow}</Text>
            <Text style={styles.actionTitle}>{a.title}</Text>
            <Text style={styles.actionDesc} numberOfLines={2}>{a.description}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Financial positions */}
      <Text style={styles.sectionTitle}>Financial Positions</Text>
      <View style={styles.positionsList}>
        {FINANCIAL_POSITIONS.map(p => (
          <View style={styles.positionRow} key={p.key}>
            <View style={styles.positionIcon}>
              <Text style={styles.positionIconText}>{p.icon}</Text>
            </View>
            <Text style={styles.positionLabel}>{p.label}</Text>
            <Text style={styles.positionValue}>$0</Text>
          </View>
        ))}
      </View>

      {/* Navigation */}
      <View style={styles.navLinks}>
        <TouchableOpacity style={styles.navLink} onPress={() => navigation.navigate('OrgSelector')}>
          <Text style={styles.navLinkText}>Switch Organization</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.navLink} onPress={logout}>
          <Text style={[styles.navLinkText, { color: Colors.error }]}>Sign Out</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

export default OrgOverviewScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { paddingBottom: Spacing.xxl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.lg },
  primaryBtn: { backgroundColor: Colors.primary, borderRadius: Radius.md, paddingVertical: 12, paddingHorizontal: Spacing.xl },
  primaryBtnText: { color: Colors.white, fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold },

  orgHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.lg,
    backgroundColor: Colors.heading,
  },
  orgAvatar: {
    width: 48,
    height: 48,
    borderRadius: Radius.md,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.md,
  },
  orgAvatarText: { color: Colors.white, fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold },
  orgInfo: { flex: 1 },
  orgName: { fontSize: Typography.fontSizeMd, fontWeight: Typography.fontWeightBold, color: Colors.white },
  orgMeta: { fontSize: Typography.fontSizeXs, color: 'rgba(255,255,255,0.65)', marginTop: 2 },
  statusBadge: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
  },
  statusText: { color: Colors.white, fontSize: Typography.fontSizeXs, fontWeight: Typography.fontWeightMedium },

  statsRow: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    gap: Spacing.sm,
    backgroundColor: Colors.muted,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  statCard: { flex: 1, alignItems: 'center' },
  statValue: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  statLabel: { fontSize: Typography.fontSizeXs, color: Colors.text, marginTop: 2 },

  sectionTitle: {
    fontSize: Typography.fontSizeSm,
    fontWeight: Typography.fontWeightSemibold,
    color: Colors.text,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    paddingBottom: Spacing.sm,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  actionCard: {
    width: '47%',
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  actionEyebrow: { fontSize: Typography.fontSizeXs, fontWeight: Typography.fontWeightSemibold, color: Colors.primary, textTransform: 'uppercase', marginBottom: 4 },
  actionTitle: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: 4 },
  actionDesc: { fontSize: Typography.fontSizeXs, color: Colors.text, lineHeight: 16 },

  positionsList: { paddingHorizontal: Spacing.lg },
  positionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  positionIcon: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    backgroundColor: Colors.muted,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.md,
  },
  positionIconText: { fontSize: Typography.fontSizeXs, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  positionLabel: { flex: 1, fontSize: Typography.fontSizeBase, color: Colors.heading },
  positionValue: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold, color: Colors.heading },

  navLinks: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.xl, gap: Spacing.sm },
  navLink: { paddingVertical: Spacing.sm },
  navLinkText: { fontSize: Typography.fontSizeBase, color: Colors.primary, fontWeight: Typography.fontWeightMedium },
});
