import './index.css';
import type { TaskStatus, StageStatus } from '@/types/task';

/**
 * 任务/阶段状态徽章（规范 §06 状态徽章形态：10% 同色底 + 同色字，500 字重，4px 12px / r12 / 12px）
 * 语义映射（设计令牌）：pending=中性 · running=accent+脉冲点 · completed=success · failed=error · paused=warning · cancelled=muted
 */
const statusTokenMap: Record<string, string> = {
  pending: 'var(--text-secondary)',
  running: 'var(--accent-color)',
  completed: 'var(--success)',
  failed: 'var(--error)',
  paused: 'var(--warning)',
  cancelled: 'var(--text-muted)',
};

const statusTextMap: Record<string, string> = {
  pending: '等待',
  running: '运行中',
  completed: '完成',
  failed: '失败',
  paused: '已暂停',
  cancelled: '已取消',
};

interface StatusBadgeProps {
  status: TaskStatus | StageStatus;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const text = statusTextMap[status] || statusTextMap.pending;
  const token = statusTokenMap[status] || statusTokenMap.pending;
  const isRunning = status === 'running';
  return (
    <span className="eakis-status-badge" style={{ color: token }}>
      <span
        className={`status-dot${isRunning ? ' is-pulsing' : ''}`}
        style={{ background: token }}
      />
      {text}
    </span>
  );
};

export default StatusBadge;
