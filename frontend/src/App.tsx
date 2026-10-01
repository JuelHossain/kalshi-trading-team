import React from 'react';
import { Cockpit } from './cockpit/Cockpit';
import Login from './components/Login';
import { useAuth } from './hooks/useAuth';

const App: React.FC = () => {
  const { isAuthenticated, authMode, isAuthenticating, authError, login, logout } = useAuth();

  if (!isAuthenticated) {
    return <Login onLogin={login} authError={authError} isAuthenticating={isAuthenticating} />;
  }

  return <Cockpit isPaperTrading={authMode !== 'production'} onSignOut={logout} />;
};

export default App;
