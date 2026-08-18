import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, ThemeMode, Note, Document } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  theme: ThemeMode;
  _hasHydrated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  setTheme: (t: ThemeMode) => void;
  setHasHydrated: (v: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      theme: "dark",
      _hasHydrated: false,
      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null }),
      setTheme: (theme) => set({ theme }),
      setHasHydrated: (v) => set({ _hasHydrated: v }),
    }),
    {
      name: "aivaura-auth",
      partialize: (state) => ({ user: state.user, token: state.token, theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

export type WorkspaceTab = "dashboard" | "ask" | "graph" | "notes" | "connectors" | "admin";

interface UIState {
  activeTab: WorkspaceTab;
  setActiveTab: (tab: WorkspaceTab) => void;
  inspectingDoc: Document | null;
  setInspectingDoc: (doc: Document | null) => void;
  editingNote: Note | null;
  setEditingNote: (note: Note | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: "dashboard",
  setActiveTab: (activeTab) => set({ activeTab }),
  inspectingDoc: null,
  setInspectingDoc: (inspectingDoc) => set({ inspectingDoc }),
  editingNote: null,
  setEditingNote: (editingNote) => set({ editingNote }),
}));
