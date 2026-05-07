import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  ActivityIndicator, RefreshControl, Modal, TextInput,
} from 'react-native';
import { teamMembersAPI, TeamMember } from '../../services/api';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

const TeamScreen: React.FC<Props> = () => {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('member');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const load = async () => {
    try {
      const data = await teamMembersAPI.getAll();
      setMembers(Array.isArray(data) ? data : []);
    } catch {}
  };

  useEffect(() => { load().finally(() => setLoading(false)); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const handleInvite = async () => {
    setFormError('');
    if (!email.trim()) { setFormError('Email is required'); return; }
    setSaving(true);
    try {
      await teamMembersAPI.create({ email: email.trim().toLowerCase(), role });
      setShowModal(false);
      setEmail('');
      await load();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to invite member');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (id: number) => {
    try {
      await teamMembersAPI.delete(id);
      await load();
    } catch {}
  };

  const ROLES = ['member', 'admin', 'viewer'];

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Team</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowModal(true)} activeOpacity={0.85}>
          <Text style={styles.addBtnText}>+ Invite</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
      ) : members.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>No team members</Text>
          <Text style={styles.emptyBody}>Invite members to your organization.</Text>
        </View>
      ) : (
        <FlatList
          data={members}
          keyExtractor={m => String(m.id)}
          renderItem={({ item }) => (
            <View style={styles.memberCard}>
              <View style={styles.memberAvatar}>
                <Text style={styles.memberAvatarText}>
                  {(item.user?.username || item.email || 'U').charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.memberInfo}>
                <Text style={styles.memberName}>{item.user?.username || item.email || 'Member'}</Text>
                <Text style={styles.memberEmail}>{item.user?.email || item.email}</Text>
                <Text style={styles.memberRole}>{item.role || 'member'}</Text>
              </View>
              <TouchableOpacity onPress={() => handleRemove(item.id)}>
                <Text style={styles.removeText}>Remove</Text>
              </TouchableOpacity>
            </View>
          )}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
        />
      )}

      <Modal visible={showModal} animationType="slide" presentationStyle="pageSheet" onRequestClose={() => setShowModal(false)}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Invite Member</Text>
          <TouchableOpacity onPress={() => setShowModal(false)}>
            <Text style={styles.modalClose}>Cancel</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.modalBody}>
          {!!formError && (
            <View style={styles.errorBox}><Text style={styles.errorText}>{formError}</Text></View>
          )}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Email *</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="member@company.com"
              placeholderTextColor={Colors.placeholder}
              autoCapitalize="none"
              keyboardType="email-address"
            />
          </View>
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Role</Text>
            <View style={styles.roleRow}>
              {ROLES.map(r => (
                <TouchableOpacity
                  key={r}
                  style={[styles.roleChip, role === r && styles.roleChipActive]}
                  onPress={() => setRole(r)}
                >
                  <Text style={[styles.roleChipText, role === r && styles.roleChipTextActive]}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
          <TouchableOpacity
            style={[styles.primaryBtn, saving && styles.btnDisabled]}
            onPress={handleInvite}
            disabled={saving}
            activeOpacity={0.85}
          >
            {saving ? <ActivityIndicator color={Colors.white} /> : <Text style={styles.primaryBtnText}>Send Invite</Text>}
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
};

export default TeamScreen;

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
  memberCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  memberAvatar: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: Colors.muted,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.md,
  },
  memberAvatarText: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  memberInfo: { flex: 1 },
  memberName: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold, color: Colors.heading },
  memberEmail: { fontSize: Typography.fontSizeXs, color: Colors.text },
  memberRole: { fontSize: Typography.fontSizeXs, color: Colors.primary, fontWeight: Typography.fontWeightMedium, textTransform: 'capitalize' },
  removeText: { color: Colors.error, fontSize: Typography.fontSizeSm },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.sm },
  emptyBody: { fontSize: Typography.fontSizeSm, color: Colors.text, textAlign: 'center' },
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
  label: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium, color: Colors.heading, marginBottom: Spacing.xs },
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
  roleRow: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap' },
  roleChip: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
  },
  roleChipActive: { backgroundColor: Colors.heading, borderColor: Colors.heading },
  roleChipText: { fontSize: Typography.fontSizeSm, color: Colors.text },
  roleChipTextActive: { color: Colors.white },
  primaryBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: Spacing.md,
  },
  btnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: Colors.white, fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold },
});
