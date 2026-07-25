import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { ROUTES } from '../lib/routes';
import { useAuth } from './AuthContext';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: 'light' | 'dark';
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { landlordUuid } = useAuth();
  const [theme, setThemeState] = useState<Theme>('system');
  
  // Compute the actual theme to render based on system preference if needed
  const getResolvedTheme = useCallback((t: Theme): 'light' | 'dark' => {
    if (t === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return t;
  }, []);

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(getResolvedTheme('system'));

  // Initial load from server or localStorage
  useEffect(() => {
    const saved = localStorage.getItem('theme') as Theme;
    if (saved) {
      setThemeState(saved);
      setResolvedTheme(getResolvedTheme(saved));
    } else if (landlordUuid) {
      // Try to fetch from server config
      fetch(ROUTES.LANDLORDAPICONFIGTHEMEGET(landlordUuid), { credentials: 'include' })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data && data.theme) {
            setThemeState(data.theme);
            setResolvedTheme(getResolvedTheme(data.theme));
            localStorage.setItem('theme', data.theme);
          }
        })
        .catch(() => {});
    }
  }, [getResolvedTheme, landlordUuid]);

  // Apply classes whenever resolvedTheme changes
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  // Handle system preference changes
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      setResolvedTheme(mediaQuery.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // Global setter that also updates server and localStorage
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    setResolvedTheme(getResolvedTheme(newTheme));
    localStorage.setItem('theme', newTheme);
    
    // Attempt to persist to server
    if (landlordUuid) {
      fetch(ROUTES.LANDLORDAPICONFIGTHEME(landlordUuid), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: newTheme }),
        credentials: 'include',
      }).catch(console.error);
    }
  }, [getResolvedTheme, landlordUuid]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
