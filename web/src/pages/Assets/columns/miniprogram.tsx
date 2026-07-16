import { Tag } from 'antd';
import RiskTag from '@/components/RiskTag';
import type { MiniProgramAsset } from '@/types/asset';
import type { RiskLevel, VulnCount } from '@/types/asset';

const platformLabels: Record<string, { text: string; color: string }> = {
  wechat: { text: '微信', color: 'green' },
  work_wechat: { text: '企业微信', color: 'blue' },
  alipay: { text: '支付宝', color: 'cyan' },
  douyin: { text: '抖音', color: 'orange' },
  other: { text: '其他', color: 'default' },
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

export const getMiniProgramColumns = (navigate: (url: string) => void) => [
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 160, ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '访问平台', dataIndex: 'platform', key: 'platform', width: 90, render: (v: string) => { const p = platformLabels[v]; return p ? <Tag color={p.color}>{p.text}</Tag> : <Tag>{v}</Tag>; } },
  { title: '访问链接', dataIndex: 'access_link', key: 'link', width: 180, ellipsis: true, render: (v: string) => v ? <code style={{ fontSize: 11, color: '#888' }}>{v.slice(0, 40)}...</code> : '-' },
  { title: '内部访问', dataIndex: 'is_internal', key: 'internal', width: 70, render: (v: boolean) => <Tag color={v ? 'orange' : 'default'}>{v ? '是' : '否'}</Tag> },
  { title: '备注', dataIndex: 'notes', key: 'notes', width: 120, ellipsis: true, render: (v: string) => v || '-' },
  { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: RiskLevel) => <RiskTag level={v} /> },
  { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: MiniProgramAsset) => renderVulnCount(r.vuln_count, r.id, navigate) },
];
