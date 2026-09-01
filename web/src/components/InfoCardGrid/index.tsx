import './index.css';

interface InfoCardGridProps {
  data: Array<{ label: string; value: string; span?: number }>;
}

/**
 * 信息网格卡（规范 §06）：.eakis-panel 形态（暗色描边 / 亮色投影）+ --radius-md，
 * hover 态与 KPI 卡一致；span=2 占双列，gap 16px（4px 刻度）。
 */
const InfoCardGrid: React.FC<InfoCardGridProps> = ({ data }) => (
  <div className="eakis-info-grid">
    {data.map((item) => (
      <div
        key={item.label}
        className="eakis-info-card"
        style={item.span === 2 ? { gridColumn: 'span 2' } : undefined}
      >
        <div className="eakis-info-card-label">{item.label}</div>
        <div className="eakis-info-card-value">{item.value || '-'}</div>
      </div>
    ))}
  </div>
);

export default InfoCardGrid;
