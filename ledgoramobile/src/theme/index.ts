// Design tokens — mirrors platform tokens.css exactly
export const Colors = {
  // Core palette
  black: '#000000',
  white: '#FFFFFF',
  accent: '#EE6C4D',
  accentHover: '#D95A3C',

  // Functional aliases
  primary: '#EE6C4D',
  background: '#FFFFFF',
  surface: '#FFFFFF',
  text: 'rgba(0,0,0,0.60)',
  heading: '#000000',
  border: 'rgba(0,0,0,0.12)',
  borderSolid: '#E0E0E0',
  error: '#EE6C4D',
  success: '#000000',
  warning: 'rgba(0,0,0,0.60)',

  // Layout
  header: '#000000',
  footer: '#000000',
  bodyBg: '#FFFFFF',
  bodyText: 'rgba(0,0,0,0.60)',

  // Surfaces
  cardBg: '#FFFFFF',
  inputBg: '#FAFAFA',
  inputBorder: 'rgba(0,0,0,0.18)',
  inputText: '#000000',
  placeholder: 'rgba(0,0,0,0.35)',

  // Badge colours
  badgeActive: '#000000',
  badgeDormant: 'rgba(0,0,0,0.40)',
  badgeType: 'rgba(0,0,0,0.60)',

  // Muted backgrounds
  muted: 'rgba(0,0,0,0.04)',
  divider: 'rgba(0,0,0,0.08)',
};

export const Typography = {
  fontSizeXs: 11,
  fontSizeSm: 13,
  fontSizeBase: 15,
  fontSizeMd: 17,
  fontSizeLg: 20,
  fontSizeXl: 24,
  fontSizeXxl: 30,
  fontSizeDisplay: 38,

  fontWeightRegular: '400' as const,
  fontWeightMedium: '500' as const,
  fontWeightSemibold: '600' as const,
  fontWeightBold: '700' as const,
  fontWeightBlack: '900' as const,

  lineHeightTight: 1.2,
  lineHeightBase: 1.5,
  lineHeightRelaxed: 1.7,
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
};

export const Radius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const Shadow = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 16,
    elevation: 8,
  },
};
