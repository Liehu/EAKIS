import { Tag } from 'antd';
import type { RiskLevel } from '@/types/asset';

const riskConfig: Record<RiskLevel, { color: string; label: string }> = {
  critical: { color: '#cf1322', label: '严重' },
  high: { color: '#d4380d', label: '高危' },
  medium: { color: '#d48806', label: '中危' },
  low: { color: '#389e0d', label: '低危' },
  info: { color: '#378ADD', label: '信息' },
};

interface RiskTagProps {
  level: RiskLevel;
}

const RiskTag: React.FC<RiskTagProps> = ({ level }) => {
  const config = riskConfig[level];
  return <Tag color={config.color} style={{ margin: 0 }}>{config.label}</Tag>;
};

export default RiskTag;
