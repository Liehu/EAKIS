import { Tag } from 'antd';
import RiskTag from '@/components/RiskTag';
import type { DomainAsset } from '@/types/asset';
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

export const getDomainColumns = (navigate: (url: string) => void) => [
  { title: '域名', dataIndex: 'domain', key: 'domain', ellipsis: true, render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
  { title: '解析记录', dataIndex: 'resolve_records', key: 'records', width: 200, render: (v: Array<{ ip: string; port: number }>) => v?.map((r, i) => <Tag key={i} style={{ fontSize: 11 }}>{r.ip}:{r.port}</Tag>) || '-' },
  { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 140, ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '关联证书', dataIndex: 'related_certs', key: 'certs', width: 160, ellipsis: true, render: (v: Array<{ subject: string }>) => v?.length ? v.map((c, i) => <Tag key={i} style={{ fontSize: 11 }} color="blue">{c.subject}</Tag>) : '-' },
  { title: 'ICP备案号', dataIndex: 'icp_number', key: 'icp', width: 150, ellipsis: true, render: (v: string) => v || '-' },
  { title: '云提供商', dataIndex: 'cloud_provider', key: 'cloud', width: 90, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
  { title: 'CDN泛解析', dataIndex: 'is_cdn_wildcard', key: 'cdn_wild', width: 80, render: (v: boolean) => <Tag color={v ? 'orange' : 'default'}>{v ? '是' : '否'}</Tag> },
  { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: RiskLevel) => <RiskTag level={v} /> },
  { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: DomainAsset) => renderVulnCount(r.vuln_count, r.id, navigate) },
];
