import { useRef, useEffect } from 'react';
import type { TaskEvent } from '@/types/task';
import './index.css';

/**
 * 日志级别语义色（设计令牌）：stage_progress=accent · agent_log/task_complete=success ·
 * vuln_found=warning · error=error；未知类型回退 --text-secondary。
 */
const logColorVar: Record<string, string> = {
  stage_progress: 'var(--accent-color)',
  agent_log: 'var(--success)',
  vuln_found: 'var(--warning)',
  task_complete: 'var(--success)',
  error: 'var(--error)',
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

/**
 * 智能体日志块（规范 §06）：--bg-secondary 底 + 1px --border-color + --radius-sm，
 * --font-mono 12px / 行高 1.5；时间戳 --text-muted、消息 --text-secondary；
 * 横向滚动兜底（行内 white-space: pre），maxHeight 滚动逻辑保持不变。
 */
const AgentLog: React.FC<AgentLogProps> = ({ events, maxHeight = 160 }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="eakis-agent-log" style={{ maxHeight }}>
      {events.map((event, i) => (
        <div key={i} className="eakis-agent-log-row">
          <span className="eakis-agent-log-time">
            {new Date(event.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
          <span
            className="eakis-agent-log-icon"
            style={{ color: logColorVar[event.event_type] || 'var(--text-secondary)' }}
          >
            {logIcons[event.event_type] || '[·]'}
          </span>
          <span className="eakis-agent-log-msg">{event.data.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default AgentLog;
