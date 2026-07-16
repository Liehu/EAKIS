import RiskTag from '@/components/RiskTag';
import type { AppAsset } from '@/types/asset';
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

export const getAppColumns = (navigate: (url: string) => void) => [
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 160, ellipsis: true, render: (v: string[]) => v?.join(', ') || '-' },
  { title: '版本', dataIndex: 'version', key: 'version', width: 80, render: (v: string) => v ? <code style={{ fontSize: 11 }}>{v}</code> : '-' },
  { title: '下载链接', dataIndex: 'download_link', key: 'link', width: 180, ellipsis: true, render: (v: string) => v ? <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: '#378ADD', fontSize: 12 }}>链接</a> : '-' },
  { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: RiskLevel) => <RiskTag level={v} /> },
  { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: AppAsset) => renderVulnCount(r.vuln_count, r.id, navigate) },
];
