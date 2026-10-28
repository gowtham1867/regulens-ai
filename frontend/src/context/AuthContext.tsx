import React, { createContext, useContext, useState, useEffect } from "react";
import type { User, UserRole } from "../types";
import { api } from "../services/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, portal?: string) => Promise<User>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem("regulens_user");
      if (!saved || saved === "undefined" || saved === "null") return null;
      return JSON.parse(saved);
    } catch (err) {
      console.warn("Failed to parse cached regulens_user from localStorage:", err);
      try {
        localStorage.removeItem("regulens_user");
      } catch {}
      return null;
    }
  });

  const [token, setToken] = useState<string | null>(() => {
    try {
      const savedToken = localStorage.getItem("regulens_token");
      if (!savedToken || savedToken === "undefined" || savedToken === "null") return null;
      return savedToken;
    } catch {
      return null;
    }
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      if (token) {
        try {
          const profile = await api.getMe();
          if (isMounted) {
            setUser(profile);
            localStorage.setItem("regulens_user", JSON.stringify(profile));
          }
        } catch (err) {
          console.warn("Initial authentication verification failed:", err);
          if (isMounted) {
            try {
              localStorage.removeItem("regulens_token");
              localStorage.removeItem("regulens_user");
            } catch {}
            setUser(null);
            setToken(null);
          }
        }
      }
      if (isMounted) {
        setIsLoading(false);
      }
    };

    initAuth();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const login = async (email: string, password: string, portal?: string): Promise<User> => {
    const data = await api.login({ email, password }, portal);
    localStorage.setItem("regulens_token", data.access_token);
    setToken(data.access_token);

    const userObj: User = {
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role as UserRole,
      is_active: true,
      institution_id: data.institution_id,
      institution_name: data.institution_name,
    };
    setUser(userObj);
    localStorage.setItem("regulens_user", JSON.stringify(userObj));
    return userObj;
  };

  const register = async (regData: any) => {
    const data = await api.register(regData);
    localStorage.setItem("regulens_token", data.access_token);
    setToken(data.access_token);

    const userObj: User = {
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role as UserRole,
      is_active: true,
      institution_id: data.institution_id,
      institution_name: data.institution_name,
    };
    setUser(userObj);
    localStorage.setItem("regulens_user", JSON.stringify(userObj));
  };

  const logout = () => {
    try {
      api.logout().catch(() => {});
    } catch {}
    localStorage.removeItem("regulens_token");
    localStorage.removeItem("regulens_user");
    setUser(null);
    setToken(null);
    window.location.href = "/login";
  };

  const hasRole = (roles: UserRole[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

