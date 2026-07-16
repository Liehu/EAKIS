import { create } from 'zustand';

interface AppState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  expandedMenus: string[];
  toggleMenu: (menuKey: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  expandedMenus: [],
  toggleMenu: (menuKey: string) =>
    set((state) => ({
      expandedMenus: state.expandedMenus.includes(menuKey)
        ? state.expandedMenus.filter((k) => k !== menuKey)
        : [...state.expandedMenus, menuKey],
    })),
}));
