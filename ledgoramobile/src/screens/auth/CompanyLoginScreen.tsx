import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { Colors, Typography, Spacing, Radius } from '../../theme';

// ---------------------------------------------------------------------------
// Company-ID Login Screen
// ---------------------------------------------------------------------------
// This replaces the standard platform login. Users authenticate with:
//   1. Company ID (slug) — scopes the session to their specific company
//   2. Email
//   3. Password
// The identity layer maps back to the same platform tokens / sessions.
// ---------------------------------------------------------------------------

interface Props {
  navigation: any;
}

const CompanyLoginScreen: React.FC<Props> = ({ navigation }) => {
  const { loginWithCompanyId } = useAuth();

  const [companyId, setCompanyId] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'company' | 'credentials'>('company');

  const handleContinue = () => {
    setError('');
    const slug = companyId.trim();
    if (!slug) {
      setError('Please enter your Company ID');
      return;
    }
    setStep('credentials');
  };

  const handleSignIn = async () => {
    setError('');
    if (!email.trim()) { setError('Please enter your email'); return; }
    if (!password) { setError('Please enter your password'); return; }

    setLoading(true);
    const result = await loginWithCompanyId(companyId.trim().toLowerCase(), email.trim(), password);
    setLoading(false);

    if (!result.success) {
      setError(result.error ?? 'Sign in failed. Please try again.');
    }
    // On success the navigator in RootNavigator will switch to AppStack automatically
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Brand mark */}
        <View style={styles.logoArea}>
          <View style={styles.logoMark}>
            <Text style={styles.logoText}>L</Text>
          </View>
          <Text style={styles.brandName}>Ledgora</Text>
        </View>

        <Text style={styles.title}>
          {step === 'company' ? 'Enter your Company ID' : 'Sign in'}
        </Text>
        <Text style={styles.subtitle}>
          {step === 'company'
            ? 'Your Company ID was assigned when your organization was created.'
            : `Signing in to ${companyId}`}
        </Text>

        {!!error && <View style={styles.errorBox}><Text style={styles.errorText}>{error}</Text></View>}

        {step === 'company' ? (
          <>
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Company ID</Text>
              <TextInput
                style={styles.input}
                value={companyId}
                onChangeText={setCompanyId}
                placeholder="your-company-id"
                placeholderTextColor={Colors.placeholder}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="next"
                onSubmitEditing={handleContinue}
              />
            </View>
            <TouchableOpacity style={styles.primaryBtn} onPress={handleContinue} activeOpacity={0.85}>
              <Text style={styles.primaryBtnText}>Continue</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Email</Text>
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="your@email.com"
                placeholderTextColor={Colors.placeholder}
                autoCapitalize="none"
                keyboardType="email-address"
                autoCorrect={false}
                returnKeyType="next"
              />
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Password</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  style={[styles.input, styles.passwordInput]}
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Enter your password"
                  placeholderTextColor={Colors.placeholder}
                  secureTextEntry={!showPassword}
                  returnKeyType="done"
                  onSubmitEditing={handleSignIn}
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
              onPress={handleSignIn}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <Text style={styles.primaryBtnText}>Sign In</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.backBtn}
              onPress={() => { setStep('company'); setError(''); }}
            >
              <Text style={styles.backBtnText}>← Back</Text>
            </TouchableOpacity>
          </>
        )}

        <View style={styles.footer}>
          <Text style={styles.footerText}>Don't have an account? </Text>
          <TouchableOpacity onPress={() => navigation.navigate('Register')}>
            <Text style={styles.linkText}>Sign up</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

export default CompanyLoginScreen;

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
    lineHeight: Typography.fontSizeSm * Typography.lineHeightRelaxed,
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
  backBtn: { alignItems: 'center', marginTop: Spacing.md },
  backBtnText: { color: Colors.text, fontSize: Typography.fontSizeSm },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: Spacing.xl },
  footerText: { color: Colors.text, fontSize: Typography.fontSizeSm },
  linkText: { color: Colors.primary, fontSize: Typography.fontSizeSm, fontWeight: Typography.fontWeightMedium },
});
