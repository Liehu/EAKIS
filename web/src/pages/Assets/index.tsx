import { useEffect, useState } from 'react';
import { Table, Tabs, Tag, Button, Drawer, Descriptions, Space, Input, Select, message, Popconfirm } from 'antd';
import { useNavigate } from 'react-router-dom';
import { getTypedAssets, getAssetFull } from '@/api/assets';
import RiskTag from '@/components/RiskTag';
import type { TypedAsset, TypedAssetType, AssetFull, VulnCount } from '@/types/asset';

// 6 类资产 Tab 配置
const TABS: { key: TypedAssetType; label: string; color: string }[] = [
  { key: 'ip', label: 'IP', color: 'blue' },
  { key: 'domain', label: '域名', color: 'green' },
  { key: 'web', label: 'Web', color: 'orange' },
  { key: 'app', label: 'APP', color: 'purple' },
  { key: 'miniprogram', label: '小程序', color: 'cyan' },
  { key: 'certificate', label: '证书', color: 'gold' },
];

const vulnTotal = (vc?: VulnCount) => (vc ? vc.critical + vc.high + vc.medium + vc.low : 0);

const Assets: React.FC = () => {
  const navigate = useNavigate();
  const [type, setType] = useState<TypedAssetType>('ip');
  const [assets, setAssets] = useState<TypedAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');
  const [riskFilter, setRiskFilter] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const [detail, setDetail] = useState<AssetFull | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const fetchAssets = async (p = page) => {
    setLoading(true);
    try {
      const res = await getTypedAssets({ asset_type: type, page: p, page_size: 20, q: q || undefined, risk: riskFilter });
      setAssets(res.data);
      setTotal(res.pagination.total);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { setPage(1); setSelectedRowKeys([]); fetchAssets(1); }, [type, q, riskFilter]); // eslint-disable-line
  useEffect(() => { fetchAssets(page); }, [page]); // eslint-disable-line

  const viewDetail = async (a: TypedAsset) => {
    setDrawerOpen(true);
    try {
      const full = await getAssetFull(a.id);
      setDetail(full);
    } catch { setDetail(null); }
  };

  const handleVulnCountClick = (e: React.MouseEvent, assetId: string) => {
    e.stopPropagation();
    navigate(`/vulnerabilities?asset_id=${assetId}`);
  };

  const handleBatchDelete = () => {
    message.success(`已删除 ${selectedRowKeys.length} 项 (mock)`);
    setSelectedRowKeys([]);
    fetchAssets();
  };

  const handleBatchEdit = () => {
    message.info(`批量编辑 ${selectedRowKeys.length} 项 (弹窗待实现)`);
  };

  // 通用列
  const commonCols = [
    {
      title: '漏洞', key: 'vuln', width: 60,
      render: (_: unknown, r: TypedAsset) => {
        const c = vulnTotal(r.vuln_count);
        return c > 0
          ? <a onClick={(e) => handleVulnCountClick(e, r.id)} style={{ color: '#ff4d4f' }}>{c}</a>
          : <span style={{ color: '#666' }}>0</span>;
      },
    },
    { title: '关联单位', dataIndex: 'company_name', key: 'company', width: 140, render: (v: string) => v || '—' },
    { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 70, render: (v: string) => <RiskTag level={v as any} /> },
    { title: '来源', dataIndex: 'source', key: 'source', width: 90, render: (v: string) => v ? <Tag>{v}</Tag> : '—' },
  ];

  // 类型专属列
  const typeColumns: Record<TypedAssetType, any[]> = {
    ip: [
      { title: 'IP', key: 'ip', ellipsis: true, render: (_: any, r: TypedAsset) => r.ip_address || (r.type_specific as any).ip_address || '—' },
      { title: '开放端口', key: 'ports', width: 140, render: (_: any, r: TypedAsset) => {
        const ports = (r.type_specific as any).open_ports;
        return typeof ports === 'string' ? ports : Array.isArray(ports) ? ports.join(', ') : '—';
      }},
      { title: '指纹', dataIndex: 'tech_stack', key: 'fp', width: 140, render: (v: string[]) => v?.slice(0, 2).map((t) => <Tag key={t}>{t}</Tag>) || '—' },
      { title: 'CDN', key: 'cdn', width: 60, render: (_: any, r: TypedAsset) => (r.type_specific as any).is_cdn ? <Tag color="orange">CDN</Tag> : '—' },
      { title: 'ASN', key: 'asn', width: 100, render: (_: any, r: TypedAsset) => (r.type_specific as any).asn || '—' },
      { title: '区域', key: 'region', width: 90, render: (_: any, r: TypedAsset) => (r.type_specific as any).region || '—' },
    ],
    domain: [
      { title: '子域名', key: 'domain', ellipsis: true, render: (_: any, r: TypedAsset) => r.domain || (r.type_specific as any).domain || '—' },
      { title: '解析IP', key: 'resolve_ip', width: 140, render: (_: any, r: TypedAsset) => r.ip_address ? `${r.ip_address}${r.port ? ':' + r.port : ''}` : '—' },
      { title: 'ICP备案号', key: 'icp', width: 140, render: (_: any, r: TypedAsset) => (r.type_specific as any).icp_license || r.icp_entity || '—' },
      { title: '注册人', key: 'registrant', width: 100, render: (_: any, r: TypedAsset) => (r.type_specific as any).registrant || '—' },
      { title: '到期', key: 'expires', width: 100, render: (_: any, r: TypedAsset) => {
        const e = (r.type_specific as any).expires_at;
        return e ? String(e).slice(0, 10) : '—';
      }},
    ],
    web: [
      { title: 'URL', key: 'url', ellipsis: true, render: (_: any, r: TypedAsset) => r.domain ? `${r.domain}${r.port ? ':' + r.port : ''}` : '—' },
      { title: '指纹', dataIndex: 'tech_stack', key: 'fp', width: 140, render: (v: string[]) => v?.slice(0, 2).map((t) => <Tag key={t}>{t}</Tag>) || '—' },
      { title: 'WAF', dataIndex: 'waf_type', key: 'waf', width: 90, render: (v: string) => v ? <Tag color="red">{v}</Tag> : '—' },
    ],
    app: [
      { title: '名称', key: 'name', ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).name || r.domain || '—' },
      { title: '包名', key: 'pkg', width: 160, ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).package_name || '—' },
      { title: '平台', key: 'platform', width: 80, render: (_: any, r: TypedAsset) => <Tag>{(r.type_specific as any).platform || '—'}</Tag> },
      { title: '版本', key: 'version', width: 70, render: (_: any, r: TypedAsset) => (r.type_specific as any).version || '—' },
      { title: '下载链接', key: 'dl', width: 80, render: (_: any, r: TypedAsset) => {
        const d = (r.type_specific as any).download_source;
        return d ? <a href={d} target="_blank" rel="noreferrer" style={{ color: '#378ADD' }}>下载</a> : '—';
      }},
    ],
    miniprogram: [
      { title: '名称', key: 'name', ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).name || r.domain || '—' },
      { title: 'AppID', key: 'appid', width: 150, render: (_: any, r: TypedAsset) => (r.type_specific as any).app_id || '—' },
      { title: '平台', key: 'platform', width: 90, render: (_: any, r: TypedAsset) => <Tag>{(r.type_specific as any).platform || 'wechat'}</Tag> },
      { title: '主体', key: 'subject', width: 140, ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).subject_entity || '—' },
      { title: '类目', key: 'category', width: 90, render: (_: any, r: TypedAsset) => (r.type_specific as any).category || '—' },
    ],
    certificate: [
      { title: '域名 (CN/SAN)', key: 'cn', ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).common_name || r.domain || '—' },
      { title: '颁发者', key: 'issuer', width: 160, ellipsis: true, render: (_: any, r: TypedAsset) => (r.type_specific as any).issuer || '—' },
      { title: '有效期至', key: 'expires', width: 110, render: (_: any, r: TypedAsset) => {
        const e = (r.type_specific as any).expires_at;
        return e ? String(e).slice(0, 10) : '—';
      }},
      { title: '状态', key: 'cert_status', width: 80, render: (_: any, r: TypedAsset) => {
        const ts = r.type_specific as any;
        if (ts.is_expired) return <Tag color="red">过期</Tag>;
        if (ts.is_self_signed) return <Tag color="orange">自签</Tag>;
        return <Tag color="green">有效</Tag>;
      }},
      { title: '签名算法', key: 'sig', width: 110, render: (_: any, r: TypedAsset) => (r.type_specific as any).signature_algorithm || '—' },
    ],
  };

  const columns = [
    ...typeColumns[type],
    ...commonCols,
    {
      title: '操作', key: 'action', width: 80,
      render: (_: unknown, r: TypedAsset) => <Button size="small" type="link" onClick={(e) => { e.stopPropagation(); viewDetail(r); }}>详情</Button>,
    },
  ];

  return (
    <div>
      <Tabs
        activeKey={type}
        onChange={(k) => setType(k as TypedAssetType)}
        items={TABS.map((t) => ({ key: t.key, label: <Tag color={t.color}>{t.label}</Tag> }))}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>{TABS.find((t) => t.key === type)?.label}资产</span>
        <Space>
          <Input.Search placeholder="搜索 IP/域名" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Select placeholder="风险等级" allowClear size="small" style={{ width: 110 }}
            value={riskFilter} onChange={setRiskFilter}
            options={[{value:'critical',label:'严重'},{value:'high',label:'高危'},{value:'medium',label:'中危'},{value:'low',label:'低危'}]} />
          {selectedRowKeys.length > 0 && (
            <>
              <span style={{ color: '#378ADD', fontSize: 12 }}>已选 {selectedRowKeys.length}</span>
              <Button size="small" onClick={handleBatchEdit}>批量编辑</Button>
              <Popconfirm title={`删除 ${selectedRowKeys.length} 项?`} onConfirm={handleBatchDelete}>
                <Button size="small" danger>批量删除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      </div>

      <Table
        size="small" loading={loading} dataSource={assets} rowKey="id"
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        onRow={(r) => ({ onClick: () => viewDetail(r), style: { cursor: 'pointer' } })}
        columns={columns}
      />

      <Drawer title={`${type.toUpperCase()} 资产详情`} open={drawerOpen} onClose={() => { setDrawerOpen(false); setDetail(null); }} width={560}>
        {detail && (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="类型"><Tag>{detail.asset_type}</Tag></Descriptions.Item>
              <Descriptions.Item label="域名/IP">{detail.domain || detail.ip_address || '—'}</Descriptions.Item>
              <Descriptions.Item label="风险"><RiskTag level={detail.risk_level as any} /></Descriptions.Item>
              <Descriptions.Item label="关联单位">{detail.company_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="指纹">{detail.tech_stack?.map((t) => <Tag key={t}>{t}</Tag>) || '—'}</Descriptions.Item>
              <Descriptions.Item label="开放端口">{detail.open_ports?.join(', ') || '—'}</Descriptions.Item>
              <Descriptions.Item label="ICP主体">{detail.icp_entity || '—'}</Descriptions.Item>
              <Descriptions.Item label="WAF">{detail.waf_type || '—'}</Descriptions.Item>
              <Descriptions.Item label="状态">{detail.status}</Descriptions.Item>
              <Descriptions.Item label="价值评分">{detail.value_score ?? '—'}</Descriptions.Item>
            </Descriptions>
            {Object.keys(detail.type_specific || {}).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>类型专属字段</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto' }}>{JSON.stringify(detail.type_specific, null, 2)}</pre>
              </div>
            )}
            {detail.vulnerabilities && detail.vulnerabilities.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>关联漏洞 ({detail.vulnerabilities.length})</div>
                {detail.vulnerabilities.map((v) => (
                  <div key={v.id} style={{ padding: '6px 0', borderBottom: '1px solid #1f2937' }}>
                    <RiskTag level={v.severity as any} /> <span>{v.title || '未命名'}</span>
                    <span style={{ color: '#666', fontSize: 11, marginLeft: 8 }}>{v.vuln_type || ''}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default Assets;
