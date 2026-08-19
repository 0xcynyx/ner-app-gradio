import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark";

const KEY = "ner-studio-theme";

// Theme lives on the root element so CSS variables can switch in one place.
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(KEY) as Theme | null;
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);
  return { theme, toggle };
}
