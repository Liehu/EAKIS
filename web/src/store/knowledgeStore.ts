import { create } from 'zustand';

interface KnowledgeState {
  activeSubModule: string | null;
  setActiveSubModule: (module: string) => void;
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  activeSubModule: null,
  setActiveSubModule: (module) => set({ activeSubModule: module }),
}));
