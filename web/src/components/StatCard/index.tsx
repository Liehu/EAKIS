import './index.css';

interface StatCardProps {
  title: string;
  value: number | string;
  color?: string;
  onClick?: () => void;
}

/**
 * KPI 统计卡（规范 §06）
 * - 结构：--bg-primary 底 + 1px --border-color 描边 + --radius-md 圆角；亮色轻投影分层
 * - 排版：标签 12px --text-secondary；数值 22px/700 --text-primary
 * - color prop 仅作为左侧小色点（严重度语义色，禁宽色条左描边）；调用方宜传 --severity-* 变量
 * - hover：暗色描边亮化为 --accent-alpha-20；亮色上浮 1px + --shadow-md
 */
const StatCard: React.FC<StatCardProps> = ({ title, value, color, onClick }) => (
  <div
    className={`eakis-kpi-card${onClick ? ' is-clickable' : ''}`}
    onClick={onClick}
  >
    <div className="eakis-kpi-card-label">
      {color && <span className="eakis-kpi-card-dot" style={{ background: color }} />}
      {title}
    </div>
    <div className="eakis-kpi-card-value">{value}</div>
  </div>
);

export default StatCard;
