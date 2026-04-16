"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ApiError, getMe, login as apiLogin, register as apiRegister, type User } from "@/lib/api";

type RegisterInput = {
  email: string;
  password: string;
  company_name?: string;
  gutachter_type?: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "gf_token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const existing = localStorage.getItem(TOKEN_KEY);
    if (!existing) {
      setIsLoading(false);
      return;
    }

    setToken(existing);
    getMe(existing)
      .then(setUser)
      .catch((error) => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
        if (error instanceof ApiError && error.status === 401) {
          toast.error("Sitzung abgelaufen, bitte erneut einloggen.");
          if (typeof window !== "undefined" && window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiLogin({ email, password });
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  };

  const register = async (input: RegisterInput) => {
    const response = await apiRegister(input);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ user, token, isLoading, login, register, logout }),
    [user, token, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

