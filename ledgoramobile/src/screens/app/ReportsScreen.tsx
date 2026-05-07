import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator, RefreshControl, TouchableOpacity,
} from 'react-native';
import { reportsAPI } from '../../services/api';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

interface Report {
  id: number;
  name?: string;
  title?: string;
  report_type?: string;
  status?: string;
  created_at?: string;
  period_start?: string;
  period_end?: string;
}

const ReportsScreen: React.FC<Props> = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const data = await reportsAPI.getAll() as { results?: Report[] } | Report[];
      const list = Array.isArray(data) ? data : (data as { results?: Report[] }).results ?? [];
      setReports(list);
    } catch {}
  };

  useEffect(() => { load().finally(() => setLoading(false)); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const handleGenerate = async (id: number) => {
    try { await reportsAPI.generate(id); } catch {}
  };

  if (loading) return (
    <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
  );

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
    >
      <Text style={styles.title}>Reports</Text>

      {reports.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>No reports yet</Text>
          <Text style={styles.emptyBody}>Reports will appear here once generated.</Text>
        </View>
      ) : (
        reports.map(r => (
          <View style={styles.card} key={r.id}>
            <View style={styles.cardHead}>
              <Text style={styles.reportName}>{r.title || r.name || `Report #${r.id}`}</Text>
              {r.status && (
                <View style={[styles.badge, r.status === 'completed' ? styles.badgeSuccess : styles.badgePending]}>
                  <Text style={styles.badgeText}>{r.status}</Text>
                </View>
              )}
            </View>
            {r.report_type && <Text style={styles.reportType}>{r.report_type}</Text>}
            {(r.period_start || r.period_end) && (
              <Text style={styles.reportPeriod}>
                {[r.period_start, r.period_end].filter(Boolean).join(' → ')}
              </Text>
            )}
            <TouchableOpacity style={styles.generateBtn} onPress={() => handleGenerate(r.id)} activeOpacity={0.85}>
              <Text style={styles.generateBtnText}>Generate</Text>
            </TouchableOpacity>
          </View>
        ))
      )}
    </ScrollView>
  );
};

export default ReportsScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: Typography.fontSizeXxl, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.lg },
  card: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  cardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: Spacing.xs },
  reportName: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading, flex: 1 },
  badge: { borderRadius: Radius.full, paddingHorizontal: Spacing.sm, paddingVertical: 3 },
  badgeSuccess: { backgroundColor: Colors.heading },
  badgePending: { backgroundColor: Colors.muted },
  badgeText: { fontSize: Typography.fontSizeXs, color: Colors.white, fontWeight: Typography.fontWeightMedium },
  reportType: { fontSize: Typography.fontSizeSm, color: Colors.text, textTransform: 'capitalize', marginBottom: 4 },
  reportPeriod: { fontSize: Typography.fontSizeXs, color: Colors.text, marginBottom: Spacing.sm },
  generateBtn: {
    borderWidth: 1,
    borderColor: Colors.heading,
    borderRadius: Radius.md,
    paddingVertical: 8,
    alignItems: 'center',
  },
  generateBtnText: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightSemibold, color: Colors.heading },
  empty: { alignItems: 'center', justifyContent: 'center', paddingTop: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.sm },
  emptyBody: { fontSize: Typography.fontSizeSm, color: Colors.text, textAlign: 'center' },
});
