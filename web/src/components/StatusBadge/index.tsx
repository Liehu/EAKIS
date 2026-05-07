import { Badge } from 'antd';
import type { TaskStatus, StageStatus } from '@/types/task';

const statusMap: Record<string, { status: 'success' | 'processing' | 'default' | 'error' | 'warning'; text: string }> = {
  pending: { status: 'default', text: '等待' },
  running: { status: 'processing', text: '运行中' },
  completed: { status: 'success', text: '完成' },
  failed: { status: 'error', text: '失败' },
  paused: { status: 'warning', text: '已暂停' },
  cancelled: { status: 'default', text: '已取消' },
};

interface StatusBadgeProps {
  status: TaskStatus | StageStatus;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = statusMap[status] || statusMap.pending;
  return <Badge status={config.status} text={<span style={{ fontSize: 12 }}>{config.text}</span>} />;
};

export default StatusBadge;
