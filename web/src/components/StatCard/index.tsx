import { Card } from 'antd';

interface StatCardProps {
  title: string;
  value: number | string;
  color?: string;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, color = '#378ADD', onClick }) => (
  <Card
    size="small"
    style={{
      background: '#1a1a2e',
      borderColor: '#2a2a4e',
      borderLeft: `3px solid ${color}`,
      cursor: onClick ? 'pointer' : 'default',
      borderRadius: 6,
    }}
    onClick={onClick}
  >
    <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>{title}</div>
    <div style={{ color: '#e2e8f0', fontSize: 22, fontWeight: 500 }}>{value}</div>
  </Card>
);

export default StatCard;
