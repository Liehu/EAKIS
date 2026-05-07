import { Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  delta?: string;
  deltaType?: 'up' | 'down';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, suffix, delta, deltaType }) => (
  <Card
    size="small"
    style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
    styles={{ body: { padding: '14px 16px' } }}
  >
    <Statistic
      title={<span style={{ fontSize: 12, color: '#888' }}>{title}</span>}
      value={value}
      suffix={suffix}
      valueStyle={{ fontSize: 22, fontWeight: 500, color: '#e0e0e0' }}
    />
    {delta && (
      <div style={{ fontSize: 11, marginTop: 4, color: deltaType === 'up' ? '#52c41a' : '#ff4d4f' }}>
        {deltaType === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {delta}
      </div>
    )}
  </Card>
);

export default MetricCard;
