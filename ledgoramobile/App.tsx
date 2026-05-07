/**
 * Ledgora Mobile
 * iOS-first implementation — transfers all platform designs, flows and logic.
 */

import React from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from './src/context/AuthContext';
import { EnterpriseProvider } from './src/context/EnterpriseContext';
import RootNavigator from './src/navigation/RootNavigator';

function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      <AuthProvider>
        <EnterpriseProvider>
          <RootNavigator />
        </EnterpriseProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

export default App;
