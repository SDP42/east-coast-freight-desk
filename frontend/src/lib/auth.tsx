import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

export interface Persona {
  key: string;
  label: string;
  description: string;
  focus: string[];
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role: string) => Promise<void>;
  logout: () => void;
}

const TOKEN_KEY = "freightdesk_token";
const AuthContext = createContext<AuthState | null>(null);

// Attach the JWT to every API call once, rather than threading it through each helper.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const getPersonas = () => api.get<Persona[]>("/auth/personas").then((r) => r.data);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      // The backend uses the OAuth2 password flow: form-encoded, email in the "username" field.
      const body = new URLSearchParams({ username: email, password });
      const { data } = await api.post<{ access_token: string }>("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      await loadUser();
    },
    [loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string, role: string) => {
      await api.post("/auth/register", { email, password, full_name: fullName || null, role });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** Turns a failed auth request into a message a person can act on. */
export function authErrorMessage(err: unknown): string {
  const anyErr = err as { response?: { status?: number; data?: { detail?: unknown } } };
  const detail = anyErr.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return "Please check the form: password needs at least 8 characters and a valid email.";
  if (!anyErr.response) return "Cannot reach the server — is the backend running?";
  return "Something went wrong. Please try again.";
}
