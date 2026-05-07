import { useEffect, useState } from 'react';
import { Card, Table, Select, Tag, Button, Drawer, Descriptions, Space } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import { getAssets } from '@/api/assets';
import RiskTag from '@/components/RiskTag';
import type { Asset, RiskLevel, AssetType } from '@/types/asset';

const Assets: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | undefined>();
  const [typeFilter, setTypeFilter] = useState<AssetType | undefined>();
  const [selected, setSelected] = useState<Asset | null>(null);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const res = await getAssets('task_01J9XXXXX', { risk: riskFilter, asset_type: typeFilter });
      setAssets(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchAssets(); }, [riskFilter, typeFilter]);

  return (
    <div>
      <Card title="资产列表" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Select placeholder="风险等级" allowClear size="small" style={{ width: 100 }} value={riskFilter} onChange={setRiskFilter}
              options={['critical', 'high', 'medium', 'low'].map((r) => ({ value: r, label: r }))} />
            <Select placeholder="资产类型" allowClear size="small" style={{ width: 100 }} value={typeFilter} onChange={setTypeFilter}
              options={['web', 'api', 'mobile', 'infra'].map((t) => ({ value: t, label: t }))} />
            <Button size="small" icon={<ExportOutlined />}>导出</Button>
          </Space>
        }>
        <Table size="small" loading={loading} dataSource={assets} rowKey="id" pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '域名', dataIndex: 'domain', key: 'domain' },
            { title: 'IP', dataIndex: 'ip_address', key: 'ip_address' },
            { title: '类型', dataIndex: 'asset_type', key: 'asset_type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '风险', dataIndex: 'risk_level', key: 'risk_level', render: (v: RiskLevel) => <RiskTag level={v} /> },
            { title: '接口数', dataIndex: 'interface_count', key: 'interface_count' },
            { title: '漏洞数', key: 'vuln_total', render: (_, r) => r.vuln_count.critical + r.vuln_count.high + r.vuln_count.medium + r.vuln_count.low },
            { title: 'ICP', dataIndex: 'icp_verified', key: 'icp', render: (v: boolean) => v ? <Tag color="green">已验证</Tag> : <Tag>未验证</Tag> },
          ]}
        />
      </Card>
      <Drawer title={selected?.domain} open={!!selected} onClose={() => setSelected(null)} width={520}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="IP 地址">{selected.ip_address}</Descriptions.Item>
            <Descriptions.Item label="资产类型">{selected.asset_type}</Descriptions.Item>
            <Descriptions.Item label="风险等级"><RiskTag level={selected.risk_level} /></Descriptions.Item>
            <Descriptions.Item label="置信度">{(selected.confidence * 100).toFixed(0)}%</Descriptions.Item>
            <Descriptions.Item label="WAF">{selected.waf_detected || '未检测到'}</Descriptions.Item>
            <Descriptions.Item label="技术栈">{selected.tech_stack.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="开放端口">{selected.open_ports.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="接口数">{selected.interface_count}</Descriptions.Item>
            <Descriptions.Item label="漏洞统计">严重 {selected.vuln_count.critical} / 高危 {selected.vuln_count.high} / 中危 {selected.vuln_count.medium} / 低危 {selected.vuln_count.low}</Descriptions.Item>
            {selected.cert_info && <Descriptions.Item label="证书">颁发者: {selected.cert_info.issuer} · 过期: {selected.cert_info.expires_at}</Descriptions.Item>}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Assets;
