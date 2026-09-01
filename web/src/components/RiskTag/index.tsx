import type { RiskLevel } from '@/types/asset';

/**
 * 风险等级标签（规范 §06）：直接复用全局 .severity-badge + .sev-*（10% 同色底 / 600 字重 / r12）
 */
const riskConfig: Record<RiskLevel, { sevClass: string; label: string }> = {
  critical: { sevClass: 'sev-critical', label: '严重' },
  high: { sevClass: 'sev-high', label: '高危' },
  medium: { sevClass: 'sev-medium', label: '中危' },
  low: { sevClass: 'sev-low', label: '低危' },
  info: { sevClass: 'sev-info', label: '信息' },
};

interface RiskTagProps {
  level: RiskLevel;
}

const RiskTag: React.FC<RiskTagProps> = ({ level }) => {
  const config = riskConfig[level];
  return (
    <span className={`severity-badge ${config.sevClass}`} style={{ margin: 0 }}>
      {config.label}
    </span>
  );
};

export default RiskTag;
