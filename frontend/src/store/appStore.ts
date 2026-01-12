import { create } from 'zustand';

interface AppState {
  activeNodeId: string | null;
  setActiveNodeId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeNodeId: null,
  setActiveNodeId: (id) => set({ activeNodeId: id }),
}));
