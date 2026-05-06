import { create } from 'zustand';
import type { Task, TaskEvent } from '@/types/task';

interface TaskState {
  currentTask: Task | null;
  setCurrentTask: (task: Task) => void;
  events: TaskEvent[];
  addEvent: (event: TaskEvent) => void;
  clearEvents: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),
  events: [],
  addEvent: (event) => set((state) => ({ events: [...state.events.slice(-200), event] })),
  clearEvents: () => set({ events: [] }),
}));
