import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getMe, login as loginRequest, register as registerRequest, updateMe } from "../../api/auth";
import { translate } from "../../lib/i18n";

const TOKEN_KEY = "token";
const LANGUAGE_KEY = "preferred_language";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [language, setLanguageState] = useState(() => localStorage.getItem(LANGUAGE_KEY) || "en");

  useEffect(() => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    getMe()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setLanguageState(me.preferredLanguage || "en");
        localStorage.setItem(LANGUAGE_KEY, me.preferredLanguage || "en");
      })
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  function applySession(data) {
    localStorage.setItem(TOKEN_KEY, data.accessToken);
    localStorage.setItem(LANGUAGE_KEY, data.user.preferredLanguage || "en");
    setToken(data.accessToken);
    setUser(data.user);
    setLanguageState(data.user.preferredLanguage || "en");
    return data.user;
  }

  async function login(email, password) {
    const data = await loginRequest(email, password);
    return applySession(data);
  }

  async function register(payload) {
    const data = await registerRequest(payload);
    return applySession(data);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  async function updateProfile(payload) {
    const updated = await updateMe(payload);
    setUser(updated);
    return updated;
  }

  async function setLanguage(lang) {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_KEY, lang);
    if (user) {
      try {
        const updated = await updateMe({ preferredLanguage: lang });
        setUser(updated);
      } catch {
        // best-effort sync; local preference still applies
      }
    }
  }

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      language,
      login,
      register,
      logout,
      updateProfile,
      setLanguage,
      t: (key) => translate(language, key),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, token, isLoading, language],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
