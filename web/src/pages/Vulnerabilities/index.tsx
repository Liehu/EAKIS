import { useEffect, useState } from 'react';
import { Table, Select, Drawer, Descriptions, Tag, Input, Button, Space, message, Popconfirm, Empty } from 'antd';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getVulnerabilities, getGlobalVulnerabilities } from '@/api/vulnerabilities';
import { getAssetFull } from '@/api/assets';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import type { Vulnerability, RiskLevel } from '@/types/vulnerability';

const severityLabel: Record<string, string> = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' };
const statusLabel: Record<string, string> = { detected: '已发现', confirmed: '已确认', false_positive: '误报', fixed: '已修复', wont_fix: '不修复', pending_review: '待审核' };
const statusColor: Record<string, string> = { detected: 'blue', confirmed: 'green', false_positive: 'default', fixed: 'cyan', wont_fix: 'orange', pending_review: 'processing' };

const Vulnerabilities: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const assetIdFilter = searchParams.get('asset_id');
  const companyIdFilter = searchParams.get('company_id');

  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selected, setSelected] = useState<Vulnerability | null>(null);
  // 漏洞详情中关联的资产信息
  const [linkedAsset, setLinkedAsset] = useState<any>(null);

  const currentTask = useTaskStore((s) => s.currentTask);
  const taskId = currentTask?.task_id;

  // 判断用全局还是任务级端点：有 asset_id/company_id 过滤或无 taskId 时用全局
  const useGlobal = !taskId || !!assetIdFilter || !!companyIdFilter;

  const fetchVulns = async (p = page) => {
    setLoading(true);
    try {
      if (useGlobal) {
        const res = await getGlobalVulnerabilities({
          severity: severityFilter, page: p, page_size: 20,
          asset_id: assetIdFilter || undefined,
          company_id: companyIdFilter || undefined,
        });
        setVulns(res.data || []);
        setTotal(res.pagination?.total || 0);
      } else {
        const res = await getVulnerabilities(taskId!, { severity: severityFilter, page: p, page_size: 20 });
        setVulns(res.data || []);
        setTotal(res.pagination?.total || 0);
      }
    } catch { setVulns([]); setTotal(0); } finally { setLoading(false); }
  };

  useEffect(() => { setPage(1); fetchVulns(1); }, [severityFilter, taskId, assetIdFilter, companyIdFilter]); // eslint-disable-line
  useEffect(() => { fetchVulns(page); }, [page]); // eslint-disable-line

  // 打开漏洞详情时，加载关联资产信息
  const openDetail = async (v: Vulnerability) => {
    setSelected(v);
    setLinkedAsset(null);
    if (v.asset_id) {
      try {
        const asset = await getAssetFull(v.asset_id);
        setLinkedAsset(asset);
      } catch { /* ignore */ }
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>
          漏洞管理
          {assetIdFilter && <Tag color="blue" style={{ marginLeft: 8 }}>已筛选资产</Tag>}
          {companyIdFilter && <Tag color="cyan" style={{ marginLeft: 8 }}>已筛选企业</Tag>}
        </span>
        <Space>
          <Input.Search placeholder="搜索" allowClear size="small" style={{ width: 160 }} />
          <Select placeholder="严重性" allowClear size="small" style={{ width: 100 }} value={severityFilter} onChange={setSeverityFilter}
            options={Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l }))} />
          {selectedRowKeys.length > 0 && (
            <>
              <span style={{ color: '#378ADD', fontSize: 12 }}>已选 {selectedRowKeys.length}</span>
              <Select size="small" placeholder="批量改状态" style={{ width: 120 }}
                onSelect={() => { message.success(`已批量改状态 ${selectedRowKeys.length} 条 (mock)`); setSelectedRowKeys([]); }}
                options={Object.entries(statusLabel).map(([k, l]) => ({ value: k, label: l }))} />
              <Popconfirm title={`删除 ${selectedRowKeys.length} 条?`} onConfirm={() => { message.success('已删除 (mock)'); setSelectedRowKeys([]); fetchVulns(); }}>
                <Button size="small" danger>批量删除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      </div>

      <Table size="small" loading={loading} dataSource={vulns} rowKey="id"
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        onRow={(record) => ({ onClick: () => openDetail(record), style: { cursor: 'pointer' } })}
        columns={[
          { title: '漏洞名称', dataIndex: 'title', key: 'title', ellipsis: true, width: 200 },
          { title: '等级', dataIndex: 'severity', key: 'severity', width: 70, render: (v: string) => <RiskTag level={v as RiskLevel} /> },
          { title: '漏洞点', key: 'target', width: 180, ellipsis: true, render: (_: any, r: any) => r.affected_path || '—' },
          { title: 'CVSS', dataIndex: 'cvss_score', key: 'cvss', width: 60 },
          { title: '发现时间', dataIndex: 'discovered_at', key: 'time', width: 100, render: (v: string) => v?.slice(0, 10) || '—' },
          { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <Tag color={statusColor[v] || 'default'}>{statusLabel[v] || v}</Tag> },
        ]}
      />

      <Drawer title={selected?.title || '漏洞详情'} open={!!selected} onClose={() => setSelected(null)} width={680}>
        {selected ? (
          <>
            <Descriptions column={2} size="small" bordered
              labelStyle={{ background: '#141422', color: '#888', width: 90 }}
              contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
              <Descriptions.Item label="漏洞名称" span={2}>{selected.title}</Descriptions.Item>
              <Descriptions.Item label="等级"><RiskTag level={selected.severity} /></Descriptions.Item>
              <Descriptions.Item label="CVSS">{selected.cvss_score || '—'}</Descriptions.Item>
              <Descriptions.Item label="类型">{selected.vuln_type ? <Tag>{selected.vuln_type}</Tag> : '—'}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor[selected.status] || 'default'}>{statusLabel[selected.status] || selected.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="漏洞点" span={2}><code style={{ color: '#378ADD' }}>{selected.affected_path || '—'}</code></Descriptions.Item>
            </Descriptions>

            {/* 关联资产（可点击跳转） */}
            <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>关联资产</div>
            {linkedAsset ? (
              <div style={{ background: '#141422', borderRadius: 6, padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Tag color="blue">{linkedAsset.asset_type}</Tag>
                    <span style={{ color: '#e2e8f0' }}>{linkedAsset.ip_address || linkedAsset.domain || linkedAsset.url || linkedAsset.name || linkedAsset.id.slice(0, 12)}</span>
                  </div>
                  <Button size="small" type="link" onClick={() => navigate(`/assets?asset=${linkedAsset.id}`)}>查看资产 →</Button>
                </div>
                {linkedAsset.company_name && (
                  <div style={{ marginTop: 8 }}>
                    <span style={{ color: '#666', fontSize: 12 }}>所属企业: </span>
                    <a style={{ color: '#378ADD', fontSize: 12 }} onClick={() => linkedAsset.company_id && navigate(`/companies?company=${linkedAsset.company_id}`)}>
                      {linkedAsset.company_name} →
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <Empty description={selected.asset_id ? '加载中...' : '无关联资产'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}

            {selected.test_payload && (
              <>
                <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>PoC / Payload</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{selected.test_payload}</pre>
              </>
            )}

            {selected.evidence && (
              <>
                <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>证据</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
{typeof selected.evidence === 'string' ? selected.evidence : JSON.stringify(selected.evidence, null, 2)}
                </pre>
              </>
            )}

            {selected.remediation && (
              <>
                <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>修复建议</div>
                <div style={{ color: '#cbd5e1' }}>{selected.remediation}</div>
              </>
            )}
          </>
        ) : <Empty />}
      </Drawer>
    </div>
  );
};

export default Vulnerabilities;
