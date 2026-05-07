import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator, RefreshControl, Modal, TextInput, ScrollView,
} from 'react-native';
import { useEnterprise } from '../../context/EnterpriseContext';
import { entitiesAPI, Entity } from '../../services/api';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

const STATUS_LABELS: Record<string, string> = {
  active: 'Active', dormant: 'Dormant', wind_down: 'Wind-Down',
  suspended: 'Suspended', archived: 'Archived', draft: 'Draft',
};
const ENTITY_TYPE_LABELS: Record<string, string> = {
  sole_proprietor: 'Sole Proprietor', llc: 'LLC', partnership: 'Partnership',
  corporation: 'Corporation', nonprofit: 'Non-Profit', subsidiary: 'Subsidiary',
  branch: 'Branch', holding_company: 'Holding Company', trust: 'Trust',
};

const ENTITY_TYPES = Object.entries(ENTITY_TYPE_LABELS).map(([k, v]) => ({ key: k, label: v }));

const EntityCard: React.FC<{ entity: Entity; onOpen: () => void; onDelete: () => void }> = ({ entity, onOpen, onDelete }) => {
  const status = STATUS_LABELS[entity.status ?? ''] || entity.status || 'Active';
  const typeLabel = ENTITY_TYPE_LABELS[entity.entity_type ?? ''] || entity.entity_type || '—';
  const initials = (entity.name || 'E').slice(0, 2).toUpperCase();

  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.avatarWrap}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardName}>{entity.name}</Text>
          <Text style={styles.cardType}>{typeLabel}</Text>
        </View>
        <View style={[styles.badge, entity.status === 'active' ? styles.badgeActive : styles.badgeDormant]}>
          <Text style={styles.badgeText}>{status}</Text>
        </View>
      </View>

      <View style={styles.cardFields}>
        {[
          { label: 'Country', value: entity.country },
          { label: 'Currency', value: entity.local_currency },
          { label: 'Reg. Number', value: entity.registration_number },
          { label: 'Fiscal Year End', value: entity.fiscal_year_end },
        ].map(f => f.value ? (
          <View style={styles.field} key={f.label}>
            <Text style={styles.fieldLabel}>{f.label}</Text>
            <Text style={styles.fieldValue}>{f.value}</Text>
          </View>
        ) : null)}
      </View>

      <View style={styles.cardActions}>
        <TouchableOpacity style={styles.openBtn} onPress={onOpen} activeOpacity={0.85}>
          <Text style={styles.openBtnText}>Open</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.deleteBtn} onPress={onDelete} activeOpacity={0.85}>
          <Text style={styles.deleteBtnText}>Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const BLANK_FORM = {
  name: '', country: '', entity_type: 'corporation', status: 'active',
  registration_number: '', local_currency: 'USD', fiscal_year_end: '',
};

const EntitiesScreen: React.FC<Props> = ({ navigation }) => {
  const { currentOrganization, entities, fetchEntities, loading } = useEnterprise();
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const reload = async () => {
    if (currentOrganization) await fetchEntities(currentOrganization.id);
  };

  useEffect(() => { reload(); }, [currentOrganization]);

  const onRefresh = async () => {
    setRefreshing(true);
    await reload();
    setRefreshing(false);
  };

  const handleCreate = async () => {
    setFormError('');
    if (!form.name.trim()) { setFormError('Entity name is required'); return; }
    if (!form.country.trim()) { setFormError('Country is required'); return; }
    setSaving(true);
    try {
      await entitiesAPI.create({ ...form, organization: currentOrganization?.id });
      setShowModal(false);
      setForm(BLANK_FORM);
      await reload();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create entity');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await entitiesAPI.delete(id);
      await reload();
    } catch {}
  };

  const set = (key: keyof typeof form) => (val: string) => setForm(f => ({ ...f, [key]: val }));

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Business Suite</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowModal(true)} activeOpacity={0.85}>
          <Text style={styles.addBtnText}>+ Add Entity</Text>
        </TouchableOpacity>
      </View>

      {loading && !refreshing ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : entities.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>No entities yet</Text>
          <Text style={styles.emptyBody}>Add your first legal entity using the button above.</Text>
        </View>
      ) : (
        <FlatList
          data={entities}
          keyExtractor={e => String(e.id)}
          renderItem={({ item }) => (
            <EntityCard
              entity={item}
              onOpen={() => navigation.navigate('EntityDashboard', { entityId: item.id })}
              onDelete={() => handleDelete(item.id)}
            />
          )}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
        />
      )}

      {/* Create Entity Modal */}
      <Modal visible={showModal} animationType="slide" presentationStyle="pageSheet" onRequestClose={() => setShowModal(false)}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>New Entity</Text>
          <TouchableOpacity onPress={() => setShowModal(false)}>
            <Text style={styles.modalClose}>Cancel</Text>
          </TouchableOpacity>
        </View>
        <ScrollView style={styles.modalBody} keyboardShouldPersistTaps="handled">
          {!!formError && (
            <View style={styles.errorBox}><Text style={styles.errorText}>{formError}</Text></View>
          )}
          {[
            { key: 'name' as const, label: 'Entity Name *', placeholder: 'Acme Corp Ltd' },
            { key: 'country' as const, label: 'Country *', placeholder: 'United States' },
            { key: 'local_currency' as const, label: 'Currency', placeholder: 'USD' },
            { key: 'registration_number' as const, label: 'Registration Number', placeholder: 'optional' },
            { key: 'fiscal_year_end' as const, label: 'Fiscal Year End', placeholder: 'YYYY-MM-DD' },
          ].map(f => (
            <View style={styles.fieldGroup} key={f.key}>
              <Text style={styles.fieldLabel}>{f.label}</Text>
              <TextInput
                style={styles.input}
                value={form[f.key]}
                onChangeText={set(f.key)}
                placeholder={f.placeholder}
                placeholderTextColor={Colors.placeholder}
                autoCorrect={false}
              />
            </View>
          ))}

          <View style={styles.fieldGroup}>
            <Text style={styles.fieldLabel}>Entity Type</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.typeScroll}>
              {ENTITY_TYPES.map(t => (
                <TouchableOpacity
                  key={t.key}
                  style={[styles.typeChip, form.entity_type === t.key && styles.typeChipActive]}
                  onPress={() => set('entity_type')(t.key)}
                >
                  <Text style={[styles.typeChipText, form.entity_type === t.key && styles.typeChipTextActive]}>
                    {t.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          <TouchableOpacity
            style={[styles.primaryBtn, saving && styles.btnDisabled]}
            onPress={handleCreate}
            disabled={saving}
            activeOpacity={0.85}
          >
            {saving ? <ActivityIndicator color={Colors.white} /> : <Text style={styles.primaryBtnText}>Create Entity</Text>}
          </TouchableOpacity>
        </ScrollView>
      </Modal>
    </View>
  );
};

export default EntitiesScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.md,
  },
  title: { fontSize: Typography.fontSizeXxl, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  addBtn: { backgroundColor: Colors.primary, borderRadius: Radius.md, paddingVertical: 8, paddingHorizontal: Spacing.md },
  addBtnText: { color: Colors.white, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightSemibold },
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
  cardTop: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.md },
  avatarWrap: {
    width: 40,
    height: 40,
    borderRadius: Radius.sm,
    backgroundColor: Colors.muted,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.sm,
  },
  avatarText: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  cardInfo: { flex: 1 },
  cardName: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  cardType: { fontSize: Typography.fontSizeXs, color: Colors.text },
  badge: { borderRadius: Radius.full, paddingHorizontal: Spacing.sm, paddingVertical: 3 },
  badgeActive: { backgroundColor: Colors.heading },
  badgeDormant: { backgroundColor: Colors.muted },
  badgeText: { fontSize: Typography.fontSizeXs, fontWeight: Typography.fontWeightMedium, color: Colors.white },
  cardFields: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, marginBottom: Spacing.md },
  field: { minWidth: '45%' },
  fieldLabel: { fontSize: Typography.fontSizeXs, color: Colors.text, marginBottom: 2 },
  fieldValue: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium, color: Colors.heading },
  cardActions: { flexDirection: 'row', gap: Spacing.sm },
  openBtn: {
    flex: 1,
    backgroundColor: Colors.heading,
    borderRadius: Radius.md,
    paddingVertical: 10,
    alignItems: 'center',
  },
  openBtnText: { color: Colors.white, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightSemibold },
  deleteBtn: {
    borderWidth: 1,
    borderColor: Colors.error,
    borderRadius: Radius.md,
    paddingVertical: 10,
    paddingHorizontal: Spacing.md,
    alignItems: 'center',
  },
  deleteBtnText: { color: Colors.error, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.sm },
  emptyBody: { fontSize: Typography.fontSizeSm, color: Colors.text, textAlign: 'center' },
  // Modal
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.divider,
  },
  modalTitle: { fontSize: Typography.fontSizeMd, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  modalClose: { color: Colors.primary, fontSize: Typography.fontSizeBase },
  modalBody: { padding: Spacing.lg },
  errorBox: {
    backgroundColor: 'rgba(238,108,77,0.10)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: Colors.error,
  },
  errorText: { color: Colors.error, fontSize: Typography.fontSizeSm },
  fieldGroup: { marginBottom: Spacing.md },
  input: {
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    fontSize: Typography.fontSizeBase,
    color: Colors.inputText,
    backgroundColor: Colors.inputBg,
  },
  typeScroll: { marginTop: Spacing.xs },
  typeChip: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    marginRight: Spacing.xs,
  },
  typeChipActive: { backgroundColor: Colors.heading, borderColor: Colors.heading },
  typeChipText: { fontSize: Typography.fontSizeSm, color: Colors.text },
  typeChipTextActive: { color: Colors.white },
  primaryBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: Spacing.md,
    marginBottom: Spacing.xxl,
  },
  btnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: Colors.white, fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold },
});
