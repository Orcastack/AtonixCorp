import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator, RefreshControl,
} from 'react-native';
import { taxAPI } from '../../services/api';
import { useEnterprise } from '../../context/EnterpriseContext';
import { Colors, Typography, Spacing, Radius, Shadow } from '../../theme';

interface Props { navigation: any; }

interface TaxCountry {
  code?: string;
  country?: string;
  name?: string;
  corporate_rate?: number;
  vat_rate?: number;
  filing_frequency?: string;
  next_deadline?: string;
  status?: string;
}

const TaxComplianceScreen: React.FC<Props> = () => {
  const { currentOrganization, entities } = useEnterprise();
  const [taxData, setTaxData] = useState<TaxCountry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const data = await taxAPI.list() as { results?: TaxCountry[] } | TaxCountry[];
      const list = Array.isArray(data) ? data : (data as { results?: TaxCountry[] }).results ?? [];
      setTaxData(list);
    } catch {}
  };

  useEffect(() => { load().finally(() => setLoading(false)); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  // Collect unique countries from entities
  const entityCountries = [...new Set(entities.map(e => e.country).filter(Boolean))];

  if (loading) return (
    <View style={styles.center}><ActivityIndicator size="large" color={Colors.primary} /></View>
  );

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
    >
      <Text style={styles.title}>Tax Compliance</Text>

      {entityCountries.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Active Jurisdictions</Text>
          <View style={styles.chipRow}>
            {entityCountries.map(c => (
              <View style={styles.chip} key={c}>
                <Text style={styles.chipText}>{c}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {taxData.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Tax Rates by Country</Text>
          {taxData.slice(0, 20).map((t, i) => (
            <View style={styles.taxCard} key={t.code ?? i}>
              <View style={styles.taxCardHead}>
                <Text style={styles.taxCountry}>{t.country || t.name || t.code}</Text>
                {t.code && <Text style={styles.taxCode}>{t.code}</Text>}
              </View>
              <View style={styles.taxRates}>
                {t.corporate_rate != null && (
                  <View style={styles.rateItem}>
                    <Text style={styles.rateLabel}>Corporate</Text>
                    <Text style={styles.rateValue}>{t.corporate_rate}%</Text>
                  </View>
                )}
                {t.vat_rate != null && (
                  <View style={styles.rateItem}>
                    <Text style={styles.rateLabel}>VAT</Text>
                    <Text style={styles.rateValue}>{t.vat_rate}%</Text>
                  </View>
                )}
                {t.filing_frequency && (
                  <View style={styles.rateItem}>
                    <Text style={styles.rateLabel}>Filing</Text>
                    <Text style={styles.rateValue}>{t.filing_frequency}</Text>
                  </View>
                )}
              </View>
              {t.next_deadline && (
                <Text style={styles.deadline}>Next deadline: {t.next_deadline}</Text>
              )}
            </View>
          ))}
        </View>
      )}

      {taxData.length === 0 && (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>No tax data available</Text>
          <Text style={styles.emptyBody}>Tax compliance data will appear here once configured.</Text>
        </View>
      )}
    </ScrollView>
  );
};

export default TaxComplianceScreen;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: Typography.fontSizeXxl, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.lg },
  section: { marginBottom: Spacing.xl },
  sectionTitle: {
    fontSize: Typography.fontSizeSm,
    fontWeight: Typography.fontWeightSemibold,
    color: Colors.text,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: Spacing.sm,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  chip: {
    backgroundColor: Colors.heading,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 5,
  },
  chipText: { color: Colors.white, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium },
  taxCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  taxCardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: Spacing.sm },
  taxCountry: { fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  taxCode: { fontSize: Typography.fontSizeXs, color: Colors.text },
  taxRates: { flexDirection: 'row', gap: Spacing.md, flexWrap: 'wrap', marginBottom: Spacing.xs },
  rateItem: {},
  rateLabel: { fontSize: Typography.fontSizeXs, color: Colors.text },
  rateValue: { fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightSemibold, color: Colors.heading },
  deadline: { fontSize: Typography.fontSizeXs, color: Colors.primary, marginTop: 4 },
  empty: { alignItems: 'center', paddingTop: Spacing.xxl },
  emptyTitle: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading, marginBottom: Spacing.sm },
  emptyBody: { fontSize: Typography.fontSizeSm, color: Colors.text, textAlign: 'center' },
});
