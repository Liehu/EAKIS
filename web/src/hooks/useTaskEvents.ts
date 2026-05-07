import { useEffect, useRef, useCallback } from 'react';
import { useTaskStore } from '@/store/taskStore';
import type { TaskEvent } from '@/types/task';

export function useTaskEvents(taskId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null);
  const addEvent = useTaskStore((s) => s.addEvent);

  const connect = useCallback(() => {
    if (!taskId) return;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'ws://localhost:8000';
    const wsUrl = baseUrl.replace(/^http/, 'ws') + `/v1/tasks/${taskId}/events`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data: TaskEvent = JSON.parse(event.data);
        addEvent(data);
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      setTimeout(connect, 3000);
    };
  }, [taskId, addEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const disconnect = () => {
    wsRef.current?.close();
    wsRef.current = null;
  };

  return { disconnect };
}
