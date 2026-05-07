import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../services/api';
import { Storage } from '../../services/storage';
import { Colors, Typography, Spacing, Radius } from '../../theme';

interface Props {
  navigation: any;
}

const RegisterScreen: React.FC<Props> = ({ navigation }) => {
  const { setActiveOrg } = useAuth();

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    orgName: '',
    country: '',
    phone: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = (key: keyof typeof form) => (val: string) =>
    setForm(f => ({ ...f, [key]: val }));

  const handleRegister = async () => {
    setError('');
    if (!form.name.trim()) { setError('Full name is required'); return; }
    if (!form.email.trim()) { setError('Email is required'); return; }
    if (!form.password) { setError('Password is required'); return; }
    if (!form.orgName.trim()) { setError('Company name is required'); return; }

    setLoading(true);
    try {
      const data = await authAPI.register({
        email: form.email.trim().toLowerCase(),
        password: form.password,
        username: form.email.trim().toLowerCase(),
        account_type: 'enterprise',
        country: form.country.trim(),
        phone: form.phone.trim(),
        org_name: form.orgName.trim(),
      });
      await Storage.set(Storage.keys.TOKEN, data.access);
      await Storage.set(Storage.keys.REFRESH_TOKEN, data.refresh);
      // Navigator will redirect to app once token is in storage — re-hydrate auth
      // by navigating back to Login and auto-signing in:
      navigation.replace('CompanyLogin');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.logoArea}>
          <View style={styles.logoMark}>
            <Text style={styles.logoText}>L</Text>
          </View>
          <Text style={styles.brandName}>Ledgora</Text>
        </View>

        <Text style={styles.title}>Create account</Text>
        <Text style={styles.subtitle}>Register your company to get started</Text>

        {!!error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {[
          { key: 'name' as const, label: 'Full Name', placeholder: 'John Smith', type: 'default' },
          { key: 'email' as const, label: 'Email', placeholder: 'your@email.com', type: 'email-address' },
          { key: 'orgName' as const, label: 'Company Name', placeholder: 'Acme Inc.', type: 'default' },
          { key: 'country' as const, label: 'Country', placeholder: 'United States', type: 'default' },
          { key: 'phone' as const, label: 'Phone (optional)', placeholder: '+1 234 567 8900', type: 'phone-pad' },
        ].map(field => (
          <View style={styles.fieldGroup} key={field.key}>
            <Text style={styles.label}>{field.label}</Text>
            <TextInput
              style={styles.input}
              value={form[field.key]}
              onChangeText={set(field.key)}
              placeholder={field.placeholder}
              placeholderTextColor={Colors.placeholder}
              autoCapitalize={field.key === 'email' ? 'none' : 'words'}
              keyboardType={field.type as any}
              autoCorrect={false}
            />
          </View>
        ))}

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Password</Text>
          <View style={styles.passwordRow}>
            <TextInput
              style={[styles.input, styles.passwordInput]}
              value={form.password}
              onChangeText={set('password')}
              placeholder="Create a password"
              placeholderTextColor={Colors.placeholder}
              secureTextEntry={!showPassword}
            />
            <TouchableOpacity
              style={styles.toggleBtn}
              onPress={() => setShowPassword(v => !v)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.toggleText}>{showPassword ? 'Hide' : 'Show'}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.primaryBtn, loading && styles.btnDisabled]}
          onPress={handleRegister}
          disabled={loading}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <Text style={styles.primaryBtnText}>Create Account</Text>
          )}
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>Already have an account? </Text>
          <TouchableOpacity onPress={() => navigation.navigate('CompanyLogin')}>
            <Text style={styles.linkText}>Sign in</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

export default RegisterScreen;

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: Colors.background },
  container: {
    flexGrow: 1,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.xxxl,
    paddingBottom: Spacing.xxl,
  },
  logoArea: { alignItems: 'center', marginBottom: Spacing.xl },
  logoMark: {
    width: 52,
    height: 52,
    borderRadius: Radius.md,
    backgroundColor: Colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  logoText: { color: Colors.white, fontSize: 28, fontWeight: Typography.fontWeightBold },
  brandName: { fontSize: Typography.fontSizeLg, fontWeight: Typography.fontWeightBold, color: Colors.heading },
  title: {
    fontSize: Typography.fontSizeXl,
    fontWeight: Typography.fontWeightBold,
    color: Colors.heading,
    textAlign: 'center',
    marginBottom: Spacing.xs,
  },
  subtitle: {
    fontSize: Typography.fontSizeSm,
    color: Colors.text,
    textAlign: 'center',
    marginBottom: Spacing.xl,
  },
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
  label: {
    fontSize: Typography.fontSizeSm,
    fontWeight: Typography.fontWeightMedium,
    color: Colors.heading,
    marginBottom: Spacing.xs,
  },
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
  passwordRow: { position: 'relative' },
  passwordInput: { paddingRight: 64 },
  toggleBtn: {
    position: 'absolute',
    right: Spacing.md,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  toggleText: { color: Colors.primary, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium },
  primaryBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  btnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: Colors.white, fontSize: Typography.fontSizeBase, fontWeight: Typography.fontWeightSemibold },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: Spacing.xl },
  footerText: { color: Colors.text, fontSize: Typography.fontSizeSm },
  linkText: { color: Colors.primary, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium },
});
