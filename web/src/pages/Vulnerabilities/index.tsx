import { useEffect, useState } from 'react';
import { Table, Select, Drawer, Descriptions, Tag, Button, Space, message, Popconfirm, Empty } from 'antd';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getVulnerabilities, getGlobalVulnerabilities } from '@/api/vulnerabilities';
import { getAssetFull } from '@/api/assets';
import RiskTag from '@/components/RiskTag';
import FilterBar from '@/components/FilterBar';
import BatchActionBar from '@/components/BatchActionBar';
import StatCard from '@/components/StatCard';
import { useTaskStore } from '@/store/taskStore';
import type { Vulnerability, VulnStatistics, RiskLevel } from '@/types/vulnerability';

/**
 * 漏洞列表（规范 §02 页面骨架 / §06 徽章）：
 * - 页面根 flex column + height 100%；页头 .eakis-page-header（标题 + FilterBar）+ 内容区 .eakis-page-content
 * - 严重度列走 RiskTag（全局 .severity-badge + sev-* 五级，中文标签保留）
 * - 状态列：语义令牌徽章（10% 同色底 + 同色字）——待处理=accent · 已确认=success · 已修复=弱化 · 误报=error · 忽略=弱化
 * - 统计 KPI 走 StatCard，severity 传对应 --severity-* 语义色（计数来自列表接口随附 summary，不新增请求）
 * - FilterBar/表格/分页走 antd 默认形态 + ConfigProvider 令牌换肤；数据获取/筛选逻辑保持不变
 */

// 严重度五级中文标签（保留原文案）
const severityLabel: Record<string, string> = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' };

// 严重度 → 语义令牌（KPI StatCard 色点用，规范 §03 五级严重度色）
const SEVERITY_TOKENS: Record<string, string> = {
  critical: 'var(--severity-critical)',
  high: 'var(--severity-high)',
  medium: 'var(--severity-medium)',
  low: 'var(--severity-low)',
  info: 'var(--severity-info)',
};

// 漏洞状态语义令牌（规范 §06 状态徽章：open=accent / confirmed=绿 / fixed=灰 / false_positive=红 / ignored=灰）
// pending_review 不在规范五态内，按"待处理"族归 accent
const STATUS_TOKENS: Record<string, { label: string; token: string }> = {
  detected: { label: '待处理', token: 'var(--accent-color)' },
  confirmed: { label: '已确认', token: 'var(--success)' },
  fixed: { label: '已修复', token: 'var(--text-muted)' },
  false_positive: { label: '误报', token: 'var(--error)' },
  wont_fix: { label: '忽略', token: 'var(--text-muted)' },
  pending_review: { label: '待审核', token: 'var(--accent-color)' },
};

// 状态徽章：10% 同色底 + 同色字（形态对齐 .severity-badge：4px 12px / r12 / 12px；状态徽章按规范 500 字重）
const VulnStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg = STATUS_TOKENS[status];
  if (!cfg) return <Tag>{status}</Tag>;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
      lineHeight: 1.2, whiteSpace: 'nowrap',
      color: cfg.token, background: 'color-mix(in srgb, currentColor 10%, transparent)',
    }}>
      {cfg.label}
    </span>
  );
};

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
  // 严重度分布统计（取列表接口随附 summary，仅用于 KPI 展示）
  const [stats, setStats] = useState<VulnStatistics | null>(null);

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
        setStats(res.summary ?? null);
      } else {
        const res = await getVulnerabilities(taskId!, { severity: severityFilter, page: p, page_size: 20 });
        setVulns(res.data || []);
        setTotal(res.pagination?.total || 0);
        setStats(res.summary ?? null);
      }
    } catch { setVulns([]); setTotal(0); setStats(null); } finally { setLoading(false); }
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">
          漏洞管理
          {assetIdFilter && <Tag color="blue" style={{ marginLeft: 8 }}>已筛选资产</Tag>}
          {companyIdFilter && <Tag color="cyan" style={{ marginLeft: 8 }}>已筛选企业</Tag>}
        </span>
        <FilterBar
          searchPlaceholder="搜索"
          onSearch={() => { /* 原页面搜索未接线，保持现状 */ }}
          filters={[
            {
              key: 'severity',
              label: '严重性',
              value: severityFilter,
              onChange: (v) => setSeverityFilter(v as RiskLevel | undefined),
              options: Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l })),
            },
          ]}
        />
      </div>
      <div className="eakis-page-content">
        {/* 统计 KPI：severity 传对应 --severity-* 语义色（规范 §03 五级严重度色） */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(severityLabel).map(([key, label]) => (
            <div key={key} style={{ flex: '1 1 120px', minWidth: 120 }}>
              <StatCard
                title={label}
                value={stats?.by_severity?.[key as RiskLevel] ?? 0}
                color={SEVERITY_TOKENS[key]}
              />
            </div>
          ))}
        </div>

        <BatchActionBar selectedCount={selectedRowKeys.length} actions={[]}>
          <Space size={8}>
            <Select size="small" placeholder="批量改状态" style={{ width: 120 }}
              onSelect={() => { message.success(`已批量改状态 ${selectedRowKeys.length} 条 (mock)`); setSelectedRowKeys([]); }}
              options={Object.entries(STATUS_TOKENS).map(([k, v]) => ({ value: k, label: v.label }))} />
            <Popconfirm title={`删除 ${selectedRowKeys.length} 条?`} onConfirm={() => { message.success('已删除 (mock)'); setSelectedRowKeys([]); fetchVulns(); }}>
              <Button size="small" danger>批量删除</Button>
            </Popconfirm>
          </Space>
        </BatchActionBar>

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
            { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <VulnStatusBadge status={v} /> },
          ]}
        />
      </div>

      <Drawer title={selected?.title || '漏洞详情'} open={!!selected} onClose={() => setSelected(null)} width={680}>
        {selected ? (
          <>
            <Descriptions column={2} size="small" bordered
              labelStyle={{ background: 'var(--bg-thead)', color: 'var(--text-secondary)', width: 90 }}
              contentStyle={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
              <Descriptions.Item label="漏洞名称" span={2}>{selected.title}</Descriptions.Item>
              <Descriptions.Item label="等级"><RiskTag level={selected.severity} /></Descriptions.Item>
              <Descriptions.Item label="CVSS">{selected.cvss_score || '—'}</Descriptions.Item>
              <Descriptions.Item label="类型">{selected.vuln_type ? <Tag>{selected.vuln_type}</Tag> : '—'}</Descriptions.Item>
              <Descriptions.Item label="状态"><VulnStatusBadge status={selected.status} /></Descriptions.Item>
              <Descriptions.Item label="漏洞点" span={2}><code style={{ color: 'var(--accent-color)', fontFamily: 'var(--font-mono)' }}>{selected.affected_path || '—'}</code></Descriptions.Item>
            </Descriptions>

            {/* 关联资产（可点击跳转） */}
            <div style={{ marginTop: 16, marginBottom: 8, color: 'var(--text-secondary)', fontSize: 12 }}>关联资产</div>
            {linkedAsset ? (
              <div style={{ background: 'var(--bg-thead)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Tag color="blue">{linkedAsset.asset_type}</Tag>
                    <span style={{ color: 'var(--text-primary)' }}>{linkedAsset.ip_address || linkedAsset.domain || linkedAsset.url || linkedAsset.name || linkedAsset.id.slice(0, 12)}</span>
                  </div>
                  <Button size="small" type="link" onClick={() => navigate(`/assets?asset=${linkedAsset.id}`)}>查看资产 →</Button>
                </div>
                {linkedAsset.company_name && (
                  <div style={{ marginTop: 8 }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>所属企业: </span>
                    <a style={{ color: 'var(--accent-color)', fontSize: 12 }} onClick={() => linkedAsset.company_id && navigate(`/companies?company=${linkedAsset.company_id}`)}>
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
                <div style={{ marginTop: 16, marginBottom: 8, color: 'var(--text-secondary)', fontSize: 12 }}>PoC / Payload</div>
                <pre style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', padding: 12, borderRadius: 'var(--radius-sm)', fontSize: 11, fontFamily: 'var(--font-mono)', overflow: 'auto', whiteSpace: 'pre-wrap', margin: 0 }}>{selected.test_payload}</pre>
              </>
            )}

            {selected.evidence && (
              <>
                <div style={{ marginTop: 16, marginBottom: 8, color: 'var(--text-secondary)', fontSize: 12 }}>证据</div>
                <pre style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', padding: 12, borderRadius: 'var(--radius-sm)', fontSize: 11, fontFamily: 'var(--font-mono)', overflow: 'auto', whiteSpace: 'pre-wrap', margin: 0 }}>
{typeof selected.evidence === 'string' ? selected.evidence : JSON.stringify(selected.evidence, null, 2)}
                </pre>
              </>
            )}

            {selected.remediation && (
              <>
                <div style={{ marginTop: 16, marginBottom: 8, color: 'var(--text-secondary)', fontSize: 12 }}>修复建议</div>
                <div style={{ color: 'var(--text-secondary)' }}>{selected.remediation}</div>
              </>
            )}
          </>
        ) : <Empty />}
      </Drawer>
    </div>
  );
};

export default Vulnerabilities;
