'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

export interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  login(token: string): void;
  logout(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);

  // Hydrate from localStorage after mount (safe for SSR)
  useEffect(() => {
    const stored = localStorage.getItem('token');
    if (stored) setToken(stored);
  }, []);

  const login = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    window.location.replace('/login');
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
