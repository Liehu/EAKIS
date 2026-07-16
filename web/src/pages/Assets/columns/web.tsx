import { Avatar, Tag } from 'antd';
import RiskTag from '@/components/RiskTag';
import type { WebAsset } from '@/types/asset';
import type { RiskLevel, VulnCount } from '@/types/asset';

const renderVulnCount = (vc: VulnCount, assetId: string, navigate: (url: string) => void) => {
  const total = vc.critical + vc.high + vc.medium + vc.low;
  if (total === 0) return <span style={{ color: '#666' }}>0</span>;
  return (
    <a onClick={(e) => { e.stopPropagation(); navigate(`/vulnerabilities?asset_id=${assetId}`); }} style={{ color: '#378ADD', cursor: 'pointer' }}>
      {total}
    </a>
  );
};

export const getWebColumns = (navigate: (url: string) => void) => [
  { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true, render: (v: string) => <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: '#378ADD', fontSize: 12 }}>{v}</a> },
  { title: 'Title', dataIndex: 'title', key: 'title', width: 180, ellipsis: true, render: (v: string) => v || '-' },
  { title: 'Icon', dataIndex: 'icon', key: 'icon', width: 40, render: (v: string) => v ? <Avatar src={v} size={24} /> : '-' },
  { title: '截图', dataIndex: 'screenshot', key: 'screenshot', width: 60, render: (v: string) => v ? <Tag color="blue">有</Tag> : <Tag>无</Tag> },
  { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 140, ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: RiskLevel) => <RiskTag level={v} /> },
  { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: WebAsset) => renderVulnCount(r.vuln_count, r.id, navigate) },
];
