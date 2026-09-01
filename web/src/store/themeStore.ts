import { create } from 'zustand';

/**
 * 主题偏好 store —— 依据规范 §03.1 三态循环 system → light → dark
 * localStorage('eakis-theme-preference')；system 态由 matchMedia 实时解析。
 * 解析结果同时写 html[data-theme]，供全局 CSS 变量层使用。
 */

export type ThemePreference = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'eakis-theme-preference';

export const THEME_CYCLE: ThemePreference[] = ['system', 'light', 'dark'];

function readStoredPreference(): ThemePreference {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark' || v === 'system') return v;
  } catch {
    /* localStorage 不可用时静默回落 */
  }
  return 'system';
}

export function resolveSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches
    ? 'light'
    : 'dark';
}

export function applyThemeToDom(theme: ResolvedTheme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  root.style.colorScheme = theme;
}

interface ThemeState {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  /** 循环切换 system → light → dark */
  cycle: () => void;
  setPreference: (p: ThemePreference) => void;
  /** 应用启动时调用：读偏好、监听系统主题变化 */
  init: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => {
  const persist = (p: ThemePreference, resolved: ResolvedTheme) => {
    try {
      localStorage.setItem(STORAGE_KEY, p);
    } catch {
      /* ignore */
    }
    applyThemeToDom(resolved);
    set({ preference: p, resolved });
  };

  return {
    preference: readStoredPreference(),
    resolved: 'dark',

    cycle: () => {
      const current = get().preference;
      const idx = THEME_CYCLE.indexOf(current);
      const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
      get().setPreference(next);
    },

    setPreference: (p) => {
      const resolved: ResolvedTheme =
        p === 'system' ? resolveSystemTheme() : p;
      persist(p, resolved);
    },

    init: () => {
      const p = readStoredPreference();
      const resolved: ResolvedTheme =
        p === 'system' ? resolveSystemTheme() : p;
      applyThemeToDom(resolved);
      set({ preference: p, resolved });

      // system 态跟随系统实时切换
      if (window.matchMedia) {
        const mq = window.matchMedia('(prefers-color-scheme: light)');
        mq.addEventListener('change', () => {
          if (get().preference === 'system') {
            const r = resolveSystemTheme();
            applyThemeToDom(r);
            set({ resolved: r });
          }
        });
      }
    },
  };
});
