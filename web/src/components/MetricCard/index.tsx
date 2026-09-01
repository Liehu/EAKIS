import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import './index.css';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  delta?: string;
  deltaType?: 'up' | 'down';
}

/**
 * KPI 指标卡（规范 §06）：与 StatCard 同一卡片规范（.eakis-kpi-card）。
 * delta 语义色：up → --success / 其余（down）→ --error，箭头方向跟随原逻辑。
 */
const MetricCard: React.FC<MetricCardProps> = ({ title, value, suffix, delta, deltaType }) => (
  <div className="eakis-kpi-card">
    <div className="eakis-kpi-card-label">{title}</div>
    <div className="eakis-kpi-card-value">
      {value}
      {suffix && <span className="eakis-kpi-card-suffix">{suffix}</span>}
    </div>
    {delta && (
      <div
        className="eakis-kpi-card-delta"
        style={{ color: deltaType === 'up' ? 'var(--success)' : 'var(--error)' }}
      >
        {deltaType === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {delta}
      </div>
    )}
  </div>
);

export default MetricCard;
