import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Colors, Typography } from '../theme';

// Auth screens
import CompanyLoginScreen from '../screens/auth/CompanyLoginScreen';
import RegisterScreen from '../screens/auth/RegisterScreen';

// App screens
import OrganizationSelectorScreen from '../screens/app/OrganizationSelectorScreen';
import OrgOverviewScreen from '../screens/app/OrgOverviewScreen';
import EntitiesScreen from '../screens/app/EntitiesScreen';
import TeamScreen from '../screens/app/TeamScreen';
import ReportsScreen from '../screens/app/ReportsScreen';
import TaxComplianceScreen from '../screens/app/TaxComplianceScreen';

// ---------------------------------------------------------------------------
// Stack types
// ---------------------------------------------------------------------------
export type AuthStackParamList = {
  CompanyLogin: undefined;
  Register: undefined;
};

export type AppStackParamList = {
  Main: undefined;
  OrgSelector: undefined;
  OrgOverview: undefined;
  Entities: undefined;
  EntityDashboard: { entityId: number };
  Team: undefined;
  Reports: undefined;
  TaxCompliance: undefined;
  CreateOrganization: undefined;
};

export type TabParamList = {
  Overview: undefined;
  Entities: undefined;
  Team: undefined;
  Reports: undefined;
};

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const AppStack = createNativeStackNavigator<AppStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

// ---------------------------------------------------------------------------
// Simple text-based tab icon (no vector-icons dependency issues)
// ---------------------------------------------------------------------------
const TabIcon: React.FC<{ label: string; focused: boolean }> = ({ label, focused }) => (
  <View style={tabIconStyles.wrap}>
    <Text style={[tabIconStyles.icon, focused && tabIconStyles.iconActive]}>
      {label}
    </Text>
  </View>
);

const tabIconStyles = StyleSheet.create({
  wrap: { alignItems: 'center' },
  icon: { fontSize: 20, color: Colors.text },
  iconActive: { color: Colors.primary },
});

// ---------------------------------------------------------------------------
// Tab Navigator
// ---------------------------------------------------------------------------
const MainTabs: React.FC = () => (
  <Tab.Navigator
    screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: Colors.primary,
      tabBarInactiveTintColor: Colors.text,
      tabBarStyle: {
        backgroundColor: Colors.white,
        borderTopColor: Colors.border,
        borderTopWidth: 1,
      },
      tabBarLabelStyle: {
        fontSize: Typography.fontSizeXs,
        fontWeight: Typography.fontWeightMedium,
      },
    }}
  >
    <Tab.Screen
      name="Overview"
      component={OrgOverviewScreen}
      options={{
        tabBarIcon: ({ focused }) => <TabIcon label="⊡" focused={focused} />,
        title: 'Overview',
      }}
    />
    <Tab.Screen
      name="Entities"
      component={EntitiesScreen}
      options={{
        tabBarIcon: ({ focused }) => <TabIcon label="◫" focused={focused} />,
        title: 'Entities',
      }}
    />
    <Tab.Screen
      name="Team"
      component={TeamScreen}
      options={{
        tabBarIcon: ({ focused }) => <TabIcon label="⊕" focused={focused} />,
        title: 'Team',
      }}
    />
    <Tab.Screen
      name="Reports"
      component={ReportsScreen}
      options={{
        tabBarIcon: ({ focused }) => <TabIcon label="≡" focused={focused} />,
        title: 'Reports',
      }}
    />
  </Tab.Navigator>
);

// ---------------------------------------------------------------------------
// Auth Stack
// ---------------------------------------------------------------------------
const AuthNavigator: React.FC = () => (
  <AuthStack.Navigator screenOptions={{ headerShown: false }}>
    <AuthStack.Screen name="CompanyLogin" component={CompanyLoginScreen} />
    <AuthStack.Screen name="Register" component={RegisterScreen} />
  </AuthStack.Navigator>
);

// ---------------------------------------------------------------------------
// App Stack
// ---------------------------------------------------------------------------
const AppNavigator: React.FC = () => (
  <AppStack.Navigator
    screenOptions={{
      headerStyle: { backgroundColor: Colors.heading },
      headerTintColor: Colors.white,
      headerTitleStyle: { fontWeight: Typography.fontWeightSemibold, fontSize: Typography.fontSizeBase },
      headerBackTitle: 'Back',
    }}
  >
    <AppStack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
    <AppStack.Screen name="OrgSelector" component={OrganizationSelectorScreen} options={{ title: 'Organizations' }} />
    <AppStack.Screen name="OrgOverview" component={OrgOverviewScreen} options={{ title: 'Overview' }} />
    <AppStack.Screen name="Entities" component={EntitiesScreen} options={{ title: 'Business Suite' }} />
    <AppStack.Screen name="EntityDashboard" component={EntitiesScreen} options={{ title: 'Entity' }} />
    <AppStack.Screen name="Team" component={TeamScreen} options={{ title: 'Team' }} />
    <AppStack.Screen name="Reports" component={ReportsScreen} options={{ title: 'Reports' }} />
    <AppStack.Screen name="TaxCompliance" component={TaxComplianceScreen} options={{ title: 'Tax Compliance' }} />
    <AppStack.Screen name="CreateOrganization" component={OrganizationSelectorScreen} options={{ title: 'Create Organization' }} />
  </AppStack.Navigator>
);

// ---------------------------------------------------------------------------
// Root Navigator — switches between Auth and App based on authentication state
// ---------------------------------------------------------------------------
const LoadingScreen: React.FC = () => (
  <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.background }}>
    <View style={{ width: 48, height: 48, borderRadius: 8, backgroundColor: Colors.accent, alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
      <Text style={{ color: Colors.white, fontSize: 24, fontWeight: '700' }}>L</Text>
    </View>
    <ActivityIndicator size="large" color={Colors.primary} />
  </View>
);

const RootNavigator: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingScreen />;

  return (
    <NavigationContainer>
      {isAuthenticated ? <AppNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
};

export default RootNavigator;
