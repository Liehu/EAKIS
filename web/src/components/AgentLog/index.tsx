import { useRef, useEffect } from 'react';
import type { TaskEvent } from '@/types/task';

const logColors: Record<string, string> = {
  stage_progress: '#378ADD',
  agent_log: '#52c41a',
  vuln_found: '#faad14',
  task_complete: '#52c41a',
  error: '#ff4d4f',
};

const logIcons: Record<string, string> = {
  stage_progress: '[→]',
  agent_log: '[✓]',
  vuln_found: '[!]',
  task_complete: '[✓]',
  error: '[✗]',
};

interface AgentLogProps {
  events: TaskEvent[];
  maxHeight?: number;
}

const AgentLog: React.FC<AgentLogProps> = ({ events, maxHeight = 160 }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div style={{ fontFamily: 'monospace', fontSize: 11, maxHeight, overflowY: 'auto', lineHeight: 1.8 }}>
      {events.map((event, i) => (
        <div key={i} style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: '#666', flexShrink: 0 }}>
            {new Date(event.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
          <span style={{ color: logColors[event.event_type] || '#888' }}>
            {logIcons[event.event_type] || '[·]'}
          </span>
          <span style={{ color: '#bbb' }}>{event.data.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default AgentLog;
