import { Tag } from 'antd';
import RiskTag from '@/components/RiskTag';
import type { IPAsset } from '@/types/asset';
import type { RiskLevel, VulnCount } from '@/types/asset';

const sourceLabels: Record<string, { text: string; color: string }> = {
  manual: { text: '用户录入', color: 'blue' },
  icp: { text: 'ICP备案', color: 'green' },
  dns_resolve: { text: '域名解析', color: 'orange' },
  smart_correlation: { text: '智能关联', color: 'purple' },
};

const renderVulnCount = (vc: VulnCount, assetId: string, navigate: (url: string) => void) => {
  const total = vc.critical + vc.high + vc.medium + vc.low;
  if (total === 0) return <span style={{ color: '#666' }}>0</span>;
  return (
    <a onClick={(e) => { e.stopPropagation(); navigate(`/vulnerabilities?asset_id=${assetId}`); }} style={{ color: '#378ADD', cursor: 'pointer' }}>
      {total}
    </a>
  );
};

export const getIPColumns = (navigate: (url: string) => void) => [
  { title: 'IP地址', dataIndex: 'ip_address', key: 'ip', width: 140, render: (v: string) => <code style={{ fontSize: 12 }}>{v}</code> },
  { title: '开放端口', dataIndex: 'open_ports', key: 'ports', width: 180, render: (v: number[]) => v?.map((p) => <Tag key={p} style={{ fontSize: 11 }}>{p}</Tag>) || '-' },
  { title: '指纹', dataIndex: 'fingerprints', key: 'fps', width: 200, render: (v: string[]) => v?.slice(0, 3).map((f) => <Tag key={f} style={{ fontSize: 11 }}>{f}</Tag>).concat(v.length > 3 ? [<Tag key="more" style={{ fontSize: 11 }}>+{v.length - 3}</Tag>] : []) || '-' },
  { title: '关联域名', dataIndex: 'related_domains', key: 'domains', ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 140, ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '来源', dataIndex: 'source', key: 'source', width: 90, render: (v: string) => { const s = sourceLabels[v]; return s ? <Tag color={s.color}>{s.text}</Tag> : <Tag>{v}</Tag>; } },
  { title: 'CDN', dataIndex: 'is_cdn', key: 'cdn', width: 60, render: (v: boolean) => <Tag color={v ? 'orange' : 'default'}>{v ? '是' : '否'}</Tag> },
  { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: RiskLevel) => <RiskTag level={v} /> },
  { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: IPAsset) => renderVulnCount(r.vuln_count, r.id, navigate) },
];
