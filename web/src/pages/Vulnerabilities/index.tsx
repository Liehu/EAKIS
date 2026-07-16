import { useEffect, useState } from 'react';
import { Table, Select, Drawer, Descriptions, Tag, Input, Button, Space, message, Popconfirm, Empty } from 'antd';
import { useSearchParams } from 'react-router-dom';
import { getVulnerabilities } from '@/api/vulnerabilities';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import type { Vulnerability, RiskLevel } from '@/types/vulnerability';

const severityLabel: Record<string, string> = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' };
const statusLabel: Record<string, string> = { detected: '已发现', confirmed: '已确认', false_positive: '误报', fixed: '已修复', wont_fix: '不修复', pending_review: '待审核' };
const statusColor: Record<string, string> = { detected: 'blue', confirmed: 'green', false_positive: 'default', fixed: 'cyan', wont_fix: 'orange', pending_review: 'processing' };

const Vulnerabilities: React.FC = () => {
  const [searchParams] = useSearchParams();
  const assetIdFilter = searchParams.get('asset_id'); // 从资产页漏洞数跳转带过来

  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | undefined>();
  const [q, setQ] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selected, setSelected] = useState<Vulnerability | null>(null);

  const currentTask = useTaskStore((s) => s.currentTask);
  const taskId = currentTask?.task_id;

  const fetchVulns = async (p = page) => {
    if (!taskId) return;
    setLoading(true);
    try {
      const res = await getVulnerabilities(taskId, { severity: severityFilter, page: p, page_size: 20 });
      let data = res.data || [];
      // 前端按 asset_id 过滤 (从资产页跳转), 后端无此参数时本地过滤
      if (assetIdFilter) {
        data = data.filter((v: any) => v.asset_id === assetIdFilter);
      }
      if (q) {
        data = data.filter((v: any) => (v.title || '').toLowerCase().includes(q.toLowerCase()) || (v.vuln_type || '').toLowerCase().includes(q.toLowerCase()));
      }
      setVulns(data);
      setTotal(data.length);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { setPage(1); fetchVulns(1); }, [severityFilter, taskId, assetIdFilter, q]); // eslint-disable-line
  useEffect(() => { fetchVulns(page); }, [page]); // eslint-disable-line

  const handleBatchStatus = async (newStatus: string) => {
    message.success(`已批量修改 ${selectedRowKeys.length} 条状态为 ${newStatus} (mock)`);
    setSelectedRowKeys([]);
  };

  const handleBatchDelete = () => {
    message.success(`已删除 ${selectedRowKeys.length} 条 (mock)`);
    setSelectedRowKeys([]);
    fetchVulns();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>
          漏洞管理 {assetIdFilter && <Tag color="blue" style={{ marginLeft: 8 }}>已筛选资产</Tag>}
        </span>
        <Space>
          <Input.Search placeholder="漏洞名称/类型" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Select placeholder="严重性" allowClear size="small" style={{ width: 100 }} value={severityFilter} onChange={setSeverityFilter}
            options={Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l }))} />
          {selectedRowKeys.length > 0 && (
            <>
              <span style={{ color: '#378ADD', fontSize: 12 }}>已选 {selectedRowKeys.length}</span>
              <Select size="small" placeholder="批量改状态" style={{ width: 120 }} onSelect={handleBatchStatus}
                options={Object.entries(statusLabel).map(([k, l]) => ({ value: k, label: l }))} />
              <Button size="small" onClick={() => message.info('复测 (mock)')}>批量复测</Button>
              <Popconfirm title={`删除 ${selectedRowKeys.length} 条?`} onConfirm={handleBatchDelete}>
                <Button size="small" danger>批量删除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      </div>

      <Table size="small" loading={loading} dataSource={vulns} rowKey="id"
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
        columns={[
          { title: '漏洞名称', dataIndex: 'title', key: 'title', ellipsis: true, width: 200 },
          { title: '等级', dataIndex: 'severity', key: 'severity', width: 70, render: (v: string) => <RiskTag level={v as RiskLevel} /> },
          { title: '漏洞描述', dataIndex: 'description', key: 'desc', ellipsis: true, render: (v: string) => v || '—' },
          { title: '漏洞点', key: 'target', width: 180, ellipsis: true, render: (_: any, r: any) => r.affected_path || r.target || r.asset_identifier || '—' },
          { title: '关联漏洞号', key: 'cve', width: 120, render: (_: any, r: any) => r.vuln_id ? <Tag>{r.vuln_id}</Tag> : '—' },
          { title: 'CVSS', dataIndex: 'cvss_score', key: 'cvss', width: 60 },
          { title: '关联PoC', key: 'poc', width: 70, render: (_: any, r: any) => r.test_payload ? <Tag color="purple">有</Tag> : '—' },
          { title: '发现时间', dataIndex: 'discovered_at', key: 'time', width: 100, render: (v: string) => v?.slice(0, 10) || '—' },
          { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <Tag color={statusColor[v] || 'default'}>{statusLabel[v] || v}</Tag> },
        ]}
      />

      <Drawer title={selected?.title || '漏洞详情'} open={!!selected} onClose={() => setSelected(null)} width={680}
        extra={selected && <Button size="small" type="primary" onClick={() => message.info('复测 (mock)')}>复测/验证</Button>}>
        {selected ? (
          <>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="漏洞名称" span={2}>{selected.title}</Descriptions.Item>
              <Descriptions.Item label="等级"><RiskTag level={selected.severity} /></Descriptions.Item>
              <Descriptions.Item label="CVSS">{selected.cvss_score || '—'}</Descriptions.Item>
              <Descriptions.Item label="类型">{selected.vuln_type ? <Tag>{selected.vuln_type}</Tag> : '—'}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor[selected.status] || 'default'}>{statusLabel[selected.status] || selected.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="漏洞点 (IP:port/url)" span={2}><code style={{ color: '#378ADD' }}>{selected.affected_path || '—'}</code></Descriptions.Item>
              <Descriptions.Item label="关联漏洞号" span={2}>{(selected as any).vuln_id ? <Tag color="blue">{(selected as any).vuln_id}</Tag> : '— (未关联知识库)'}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>{selected.description || '—'}</Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>指纹</div>
            <div>{(selected as any).fingerprint || selected.vuln_type || '—'}</div>

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

            <div style={{ marginTop: 16, marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>同一漏洞的关联资产</div>
            <Empty description="暂无关联资产数据 (需后端跨资产漏洞关联)" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </>
        ) : <Empty />}
      </Drawer>
    </div>
  );
};

export default Vulnerabilities;
