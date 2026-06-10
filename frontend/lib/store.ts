import { create } from "zustand";

type AppState = {
  activeView: string;
  energyMode: string;
  selectedResourceId?: string;
  selectedTaskId?: string;
  setActiveView: (view: string) => void;
  setEnergyMode: (mode: string) => void;
  setSelectedResourceId: (id?: string) => void;
  setSelectedTaskId: (id?: string) => void;
};

export const useAppStore = create<AppState>((set) => ({
  activeView: "dashboard",
  energyMode: "focus",
  selectedResourceId: undefined,
  selectedTaskId: undefined,
  setActiveView: (activeView) => set({ activeView }),
  setEnergyMode: (energyMode) => set({ energyMode }),
  setSelectedResourceId: (selectedResourceId) => set({ selectedResourceId }),
  setSelectedTaskId: (selectedTaskId) => set({ selectedTaskId })
}));
