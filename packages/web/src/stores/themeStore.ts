import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark'

export function applyThemeToDocument(theme: ThemeMode) {
  document.documentElement.setAttribute('data-theme', theme)
}

function themeFromDom(): ThemeMode {
  if (typeof document === 'undefined') return 'light'
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
}

type ThemeState = {
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: themeFromDom(),
      setTheme: (theme) => {
        applyThemeToDocument(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark'
        applyThemeToDocument(next)
        set({ theme: next })
      },
    }),
    {
      name: 'dealscannr.theme',
      partialize: (s) => ({ theme: s.theme }),
      onRehydrateStorage: () => (state) => {
        if (state?.theme) applyThemeToDocument(state.theme)
      },
    },
  ),
)
