import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'sgf_theme';
const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'dark' ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      toggleTheme: () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark')),
    }),
    [theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
