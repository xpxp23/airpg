"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User } from "@/types";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    const token = api.getToken();
    if (token) {
      try {
        const userData = await api.getMe();
        setUser(userData);
      } catch {
        api.setToken(null);
      }
    }
    setLoading(false);
  }

  async function login(email: string, password: string) {
    const result = await api.login(email, password);
    api.setToken(result.access_token);
    setUser(result.user);
    router.push("/games");
  }

  async function register(username: string, email: string, password: string) {
    const result = await api.register(username, email, password);
    api.setToken(result.access_token);
    setUser(result.user);
    router.push("/games");
  }

  function logout() {
    api.setToken(null);
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
