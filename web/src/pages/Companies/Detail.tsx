import { useEffect, useState } from 'react';
import { Tabs, Table, Tag, Button, Space, Spin, Empty, Descriptions, Modal, message, Radio } from 'antd';
import { ArrowLeftOutlined, DeleteOutlined, EditOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import {
  getCompanyDetail,
  getCompanyAssets,
  getCompanyVulnerabilities,
  getCompanyRisk,
  getCompanyGraph,
  enrichCompany,
  confirmEnrichment,
} from '@/api/companies';
import RiskTag from '@/components/RiskTag';
import { useGraphStore } from '@/store/graphStore';
import type { CompanyDetailFull, SubCompany, CompanyRisk, FieldConflict, EnrichmentResponse } from '@/types/company';
import { useNavigate } from 'react-router-dom';

/**
 * 企业详情页（规范 §02 页面骨架 / §05 面板）：
 * - 页面根 flex column + height 100%；内容区 .eakis-page-content 内滚动
 * - 详情头部 / 企业信息区以 .eakis-panel 承载 + padding 16（暗色描边分层 / 亮色轻投影）
 * - 标签一律语义令牌（§03）；antd 组件保持默认形态随 ConfigProvider 换肤
 * - 图谱不在本页内嵌：股权拓扑经 graphStore 推给右侧 GraphPanel 渲染（ECharts 规则由其承接）
 * - 详情逻辑、数据获取保持不变
 */

const industryLabels: Record<string, string> = {
  fintech: '金融科技', ecommerce: '电商', tech: '互联网',
  government: '政务', healthcare: '医疗', security: '安全服务',
  cloud: '云计算', data_security: '数据安全', research: '安全研究',
  telecom: '通信', education: '教育', energy: '能源',
  logistics: '物流', gaming: '游戏', iot: '物联网',
  edtech: '教育科技', ai: '人工智能', cold_chain: '冷链',
  express: '快递', warehouse: '仓储', hardware: '硬件',
};

// 下属单位状态 → 语义令牌：活跃=success · 停用=中性弱化 · 归档=warning（§03 语义色）
const statusLabels: Record<string, { text: string; token: string }> = {
  active: { text: '活跃', token: 'var(--success)' },
  inactive: { text: '停用', token: 'var(--text-muted)' },
  archived: { text: '归档', token: 'var(--warning)' },
};

// 存续状态语义令牌（与企业管理列表页 bizStatusToken 同一映射）：存续=success · 迁出=warning · 其余中性弱化
const bizStatusToken = (v: string) =>
  v === '存续' ? 'var(--success)' : v === '迁出' ? 'var(--warning)' : 'var(--text-muted)';

// 漏洞状态语义令牌（与漏洞列表页状态徽章同一映射，保证跨页一致）：
// 待处理=accent · 已确认=success · 已修复=弱化 · 误报=error · 忽略=弱化；待审核不在规范五态内，按"待处理"族归 accent
const vulnStatusTokens: Record<string, { text: string; token: string }> = {
  detected: { text: '待处理', token: 'var(--accent-color)' },
  confirmed: { text: '已确认', token: 'var(--success)' },
  fixed: { text: '已修复', token: 'var(--text-muted)' },
  false_positive: { text: '误报', token: 'var(--error)' },
  wont_fix: { text: '忽略', token: 'var(--text-muted)' },
  pending_review: { text: '待审核', token: 'var(--accent-color)' },
};

// 资产类型语义令牌（与资产页 TYPE_TOKENS 同一映射，保证跨页一致）：
// IP=success · 域名=brand-ai-end · Web=accent · APP=warning · 小程序=severity-low
const ASSET_TYPE_TOKENS: Record<string, string> = {
  ip: 'var(--success)',
  domain: 'var(--brand-ai-end)',
  web: 'var(--accent-color)',
  app: 'var(--warning)',
  miniprogram: 'var(--severity-low)',
};

// 语义状态徽章：10% 同色底 + 同色字（§06 状态徽章形态，4px 12px / r12 / 12px / 500 字重）
const TokenBadge: React.FC<{ text: string; token: string }> = ({ text, token }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: token, background: 'color-mix(in srgb, currentColor 10%, transparent)',
  }}>{text}</span>
);

interface DetailProps {
  companyId: string;
  onBack: () => void;
  onSelectCompany?: (id: string) => void;
}

const CompanyDetail: React.FC<DetailProps> = ({ companyId, onBack, onSelectCompany }) => {
  const [detail, setDetail] = useState<CompanyDetailFull | null>(null);
  const [loading, setLoading] = useState(true);
  // S1: real cascade data (replaces direct mock imports)
  const [companyAssets, setCompanyAssets] = useState<any[]>([]);
  const [companyVulns, setCompanyVulns] = useState<any[]>([]);
  const [risk, setRisk] = useState<CompanyRisk | null>(null);
  const navigate = useNavigate();
  // 采集相关状态
  const [enriching, setEnriching] = useState(false);
  const [enrichResult, setEnrichResult] = useState<EnrichmentResponse | null>(null);
  const [conflictModalOpen, setConflictModalOpen] = useState(false);
  const [conflictChoices, setConflictChoices] = useState<Record<string, 'old' | 'new'>>({});
  const [confirming, setConfirming] = useState(false);
  // 推送股权拓扑到右侧关系图谱
  const setGraphData = useGraphStore((s) => s.setGraphData);
  const selectNode = useGraphStore((s) => s.selectNode);
  const setNodeNavigate = useGraphStore((s) => s.setNodeNavigate);

  // 注册图谱节点导航回调：点击图谱节点 → 切换到该企业详情
  useEffect(() => {
    setNodeNavigate((id: string) => {
      if (id !== companyId && onSelectCompany) {
        onSelectCompany(id);
      }
    });
    return () => setNodeNavigate(null);
  }, [companyId, onSelectCompany, setNodeNavigate]);

  const fetchDetail = () => {
    setLoading(true);
    getCompanyDetail(companyId)
      .then(setDetail)
      .finally(() => setLoading(false));
  };

  // 拉取股权拓扑并推入 graphStore（供右侧 GraphPanel 渲染）
  const fetchGraph = () => {
    getCompanyGraph(companyId, { depth: 3, holding_ratio_min: 0, include_minority: true })
      .then((g) => {
        selectNode(companyId);
        setGraphData(
          g.nodes.map((n) => ({
            id: n.id,
            name: n.name,
            depth: n.depth,
            holding_ratio: n.holding_ratio ?? null,
          })),
          g.edges.map((e) => ({
            source: e.source,
            target: e.target,
            holding_ratio: e.holding_ratio ?? null,
          })),
        );
      })
      .catch(() => setGraphData([], []));
  };

  useEffect(() => {
    fetchDetail();
    fetchGraph();
    // S1 cascade queries (de-mock)
    getCompanyAssets(companyId, { page: 1, page_size: 100 })
      .then((res) => setCompanyAssets(res.data || []))
      .catch(() => setCompanyAssets([]));
    getCompanyVulnerabilities(companyId, { page: 1, page_size: 100 })
      .then((res) => setCompanyVulns(res.data || []))
      .catch(() => setCompanyVulns([]));
    getCompanyRisk(companyId)
      .then(setRisk)
      .catch(() => setRisk(null));
  }, [companyId]);

  // 触发采集
  const handleEnrich = async () => {
    setEnriching(true);
    try {
      const res = await enrichCompany(companyId, {
        strategy: 'auto_fill',
        depth: 3,
        holding_min: 50,
        recursive_depth: 1, // 递归采集子公司→孙公司（三级穿透）
      });
      setEnrichResult(res);
      if (res.conflicts.length > 0) {
        // 初始化默认选择：全部采用新值
        const init: Record<string, 'old' | 'new'> = {};
        res.conflicts.forEach((c) => { init[c.field] = 'new'; });
        setConflictChoices(init);
        setConflictModalOpen(true);
      }
      message.success(`已从${res.provider}采集，新增 ${res.new_relations} 家关联企业${res.conflicts.length ? `，${res.conflicts.length} 项字段待确认` : ''}`);
      fetchDetail();
      fetchGraph(); // 采集后刷新股权拓扑
    } catch {
      message.error('采集失败，请检查云图 session 配置');
    } finally {
      setEnriching(false);
    }
  };

  // 冲突确认提交
  const handleConfirmConflicts = async () => {
    if (!enrichResult) return;
    setConfirming(true);
    try {
      const resolutions = enrichResult.conflicts.map((c) => ({
        field: c.field,
        accepted_value: conflictChoices[c.field] === 'old' ? c.old_value : c.new_value,
      }));
      await confirmEnrichment(companyId, resolutions);
      message.success('字段冲突已处理');
      setConflictModalOpen(false);
      fetchDetail();
    } catch {
      message.error('冲突处理失败');
    } finally {
      setConfirming(false);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  if (!detail) return <Empty description="企业不存在" />;

  const handleVulnCountClick = (assetId: string) => {
    navigate(`/vulnerabilities?asset_id=${assetId}`);
  };

  const subColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true,
      render: (text: string, record: SubCompany) =>
        onSelectCompany ? (
          <a onClick={() => onSelectCompany(record.id)} style={{ color: 'var(--accent-color)', cursor: 'pointer' }}>{text}</a>
        ) : text,
    },
    { title: '全称', dataIndex: 'full_name', key: 'full_name', ellipsis: true, width: 180 },
    { title: '信用代码', dataIndex: 'credit_code', key: 'credit_code', width: 160, ellipsis: true },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 90, render: (v: string) => <Tag>{industryLabels[v] || v}</Tag> },
    { title: '关键词', dataIndex: 'keywords', key: 'keywords', width: 160, render: (v: string[]) => v?.map((k) => <Tag key={k}>{k}</Tag>) || '-' },
    { title: '域名', dataIndex: 'domains', key: 'domains', width: 140, render: (v: string[]) => v?.join(', ') || '-' },
    { title: '官网', dataIndex: 'website', key: 'website', width: 120, ellipsis: true, render: (v: string) => v ? <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-color)' }}>{v.replace(/^https?:\/\//, '')}</a> : '-' },
    { title: '法人', dataIndex: 'legal_person', key: 'legal_person', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 60, render: (v: string) => { const s = statusLabels[v]; return s ? <TokenBadge text={s.text} token={s.token} /> : <Tag>{v}</Tag>; } },
    { title: '工号规则', dataIndex: 'work_id_rule', key: 'work_id_rule', width: 90 },
    { title: '备注', dataIndex: 'notes', key: 'notes', width: 120, ellipsis: true },
    {
      title: '操作', key: 'action', width: 80, fixed: 'right' as const,
      render: (_: unknown, _r: SubCompany) => (
        <Space size="small">
          <Button size="small" type="link" icon={<EditOutlined />}>编辑</Button>
          <Button size="small" type="link" danger icon={<DeleteOutlined />} />
        </Space>
      ),
    },
  ];

  // S1: vulns come from the cascade API (de-mocked). asset-type label mapping.
  const vulnData = companyVulns;
  const ASSET_TYPE_LABEL: Record<string, string> = {
    ip: 'IP', domain: '域名', web: 'Web', app: 'APP', miniprogram: '小程序', certificate: '证书', api: 'API', infra: '基础设施', mobile: '移动端',
  };

  const vulnColumns = [
    { title: '漏洞名称', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '等级', dataIndex: 'severity', key: 'severity', width: 70, render: (v: string) => <RiskTag level={v as any} /> },
    { title: '漏洞点', dataIndex: 'asset_identifier', key: 'asset_identifier', width: 180, ellipsis: true, render: (_v: string, r: any) => r.affected_path || '-' },
    { title: '关联编号', dataIndex: 'vuln_id', key: 'vuln_id', width: 130, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 70, render: (v: string) => { const cfg = vulnStatusTokens[v]; return cfg ? <TokenBadge text={cfg.text} token={cfg.token} /> : <Tag>{v}</Tag>; } },
    { title: '发现时间', dataIndex: 'discovered_at', key: 'discovered_at', width: 110, render: (v: string) => v?.slice(0, 10) },
  ];

  const renderVulnCount = (vc: { critical: number; high: number; medium: number; low: number }, assetId: string) => {
    const total = vc.critical + vc.high + vc.medium + vc.low;
    if (total === 0) return <span style={{ color: 'var(--text-muted)' }}>0</span>;
    return (
      <a
        onClick={(e) => { e.stopPropagation(); handleVulnCountClick(assetId); }}
        style={{ color: 'var(--accent-color)', cursor: 'pointer' }}
      >
        {total}
      </a>
    );
  };

  // S1: derive asset summary + list from real cascade data.
  const byType: Record<string, number> = {};
  for (const a of companyAssets) {
    const t = a.asset_type || 'other';
    byType[t] = (byType[t] || 0) + 1;
  }
  const assetSummary = { total: companyAssets.length, by_type: byType };
  const totalVulns = risk?.vuln_count ?? companyVulns.length;

  const companyAssetsList = companyAssets.map((a: any, i: number) => ({
    ...a,
    _category: ASSET_TYPE_LABEL[a.asset_type] || a.asset_type || '其他',
    _rowKey: `asset_${companyId}_${i}`,
  }));

  const tabItems = [
    {
      key: 'info',
      label: '企业信息',
      children: (
        <div className="eakis-panel" style={{ padding: 16, maxWidth: 960 }}>
          <Descriptions
            bordered
            size="small"
            column={2}
            colon={false}
            labelStyle={{ background: 'var(--bg-thead)', color: 'var(--text-secondary)', fontWeight: 400, padding: '10px 16px', whiteSpace: 'nowrap' }}
            contentStyle={{ background: 'var(--bg-primary)', color: 'var(--text-primary)', padding: '10px 16px' }}
          >
            <Descriptions.Item label="企业名称">{detail.name}</Descriptions.Item>
            <Descriptions.Item label="行业">{industryLabels[detail.industry] || detail.industry}</Descriptions.Item>
            <Descriptions.Item label="存续状态">{detail.business_status || '-'}</Descriptions.Item>
            <Descriptions.Item label="信用代码">{detail.credit_code || '-'}</Descriptions.Item>
            <Descriptions.Item label="法人">{detail.legal_person || '-'}</Descriptions.Item>
            <Descriptions.Item label="工号规则">{detail.work_id_rule || '-'}</Descriptions.Item>
            <Descriptions.Item label="关联域名">{detail.domains?.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="IP 范围">{detail.ip_ranges?.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="子单位数">{String(detail.sub_company_count ?? 0)}</Descriptions.Item>
            <Descriptions.Item label="数据来源">{detail.data_source ? <Tag>{detail.data_source}</Tag> : '-'}</Descriptions.Item>
            <Descriptions.Item label="最近任务状态">{detail.latest_task_status || '-'}</Descriptions.Item>
            <Descriptions.Item label="层级">{String(detail.hierarchy_level ?? 1)}</Descriptions.Item>
            <Descriptions.Item label="关键词" span={2}>{detail.keywords?.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{detail.notes || '-'}</Descriptions.Item>
          </Descriptions>
        </div>
      ),
    },
    {
      key: 'subs',
      label: `下属单位 (${detail.sub_companies?.length ?? 0})`,
      children: (
        <Table
          size="small" dataSource={detail.sub_companies} rowKey="id"
          pagination={false} scroll={{ x: 1400 }}
          columns={subColumns}
        />
      ),
    },
    {
      key: 'assets',
      label: `企业资产 (${assetSummary.total})`,
      children: (
        <div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            {[
              { label: 'IP', type: 'ip', count: assetSummary.by_type.ip || 0 },
              { label: '域名', type: 'domain', count: assetSummary.by_type.domain || 0 },
              { label: 'Web', type: 'web', count: assetSummary.by_type.web || 0 },
              { label: 'APP', type: 'app', count: assetSummary.by_type.app || 0 },
              { label: '小程序', type: 'miniprogram', count: assetSummary.by_type.miniprogram || 0 },
            ].map((item) => (
              <div key={item.label} style={{ background: 'var(--bg-thead)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', minWidth: 80, textAlign: 'center' }}>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{item.label}</div>
                <div style={{ color: ASSET_TYPE_TOKENS[item.type], fontSize: 18, fontWeight: 500 }}>{item.count}</div>
              </div>
            ))}
          </div>
          <Table size="small" dataSource={companyAssetsList}
            rowKey="_rowKey" pagination={false}
            onRow={(r: any) => ({ onClick: () => navigate(`/assets?asset=${r.id}`), style: { cursor: 'pointer' } })}
            columns={[
              { title: '类型', dataIndex: '_category', key: 'cat', width: 60, render: (v: string) => <Tag>{v}</Tag> },
              { title: '标识', key: 'identifier', ellipsis: true, render: (_: any, r: any) => <a style={{ color: 'var(--accent-color)' }}>{r.ip_address || r.domain || r.url || r.name || '-'}</a> },
              { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 150, render: (v: string[]) => v?.join(', ') || '-' },
              { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: string) => <RiskTag level={v as any} /> },
              { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: any) => renderVulnCount(r.vuln_count, r.id) },
              { title: '操作', key: 'act', width: 70, render: (_: any, r: any) => <Button size="small" type="link" onClick={(e) => { e.stopPropagation(); navigate(`/assets?asset=${r.id}`); }}>详情</Button> },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'risks',
      label: `企业风险 (${totalVulns})`,
      children: (
        <Table size="small" dataSource={vulnData} rowKey="id" pagination={false} columns={vulnColumns}
          onRow={(r: any) => ({ onClick: () => navigate(`/vulnerabilities?company_id=${companyId}&asset_id=${r.asset_id}`), style: { cursor: 'pointer' } })}
        />
      ),
    },
    {
      key: 'osint',
      label: `开源情报 (0)`,
      children: (
        <Empty description="暂无开源情报数据" />
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-content">
        {/* 详情头部：.eakis-panel + padding 16（标题 16/600，meta 走 --text-muted 弱对比位） */}
        <div className="eakis-panel" style={{ padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <Button size="small" icon={<ArrowLeftOutlined />} onClick={onBack}>返回列表</Button>
            <span style={{ color: 'var(--text-primary)', fontSize: 16, fontWeight: 600 }}>{detail.name}</span>
            {detail.business_status && <TokenBadge text={detail.business_status} token={bizStatusToken(detail.business_status)} />}
            <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>
              资产 {assetSummary.total} · 漏洞 {totalVulns} · 风险 {Math.round(risk?.risk_score ?? 0)}
            </span>
            <div style={{ flex: 1 }} />
            <Button
              type="primary"
              icon={<CloudDownloadOutlined />}
              loading={enriching}
              onClick={handleEnrich}
            >
              从云图采集关联企业
            </Button>
          </div>
        </div>

        <Tabs defaultActiveKey="info" items={tabItems} />
      </div>

      {/* 字段冲突对比 Modal */}
      <Modal
        title="采集字段冲突对比"
        open={conflictModalOpen}
        onCancel={() => setConflictModalOpen(false)}
        onOk={handleConfirmConflicts}
        confirmLoading={confirming}
        okText="提交选择"
        cancelText="取消"
        width={720}
      >
        <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
          以下字段在现有数据与采集数据间存在差异，请逐项选择保留的值。
        </p>
        <Table
          size="small"
          rowKey="field"
          dataSource={enrichResult?.conflicts || []}
          pagination={false}
          columns={[
            { title: '字段', dataIndex: 'field', key: 'field', width: 120 },
            {
              title: '现有值',
              key: 'old',
              render: (_: unknown, r: FieldConflict) =>
                r.old_value === null || r.old_value === undefined || r.old_value === ''
                  ? <span style={{ color: 'var(--text-muted)' }}>(空)</span>
                  : String(r.old_value),
            },
            {
              title: '采集值',
              key: 'new',
              render: (_: unknown, r: FieldConflict) => String(r.new_value ?? '(空)'),
            },
            {
              title: '来源',
              key: 'src',
              width: 140,
              render: (_: unknown, r: FieldConflict) => (
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  {r.old_source || '-'} → {r.new_source || '-'}
                </span>
              ),
            },
            {
              title: '选择',
              key: 'choice',
              width: 160,
              render: (_: unknown, r: FieldConflict) => (
                <Radio.Group
                  value={conflictChoices[r.field] || 'new'}
                  onChange={(e) => setConflictChoices((prev) => ({ ...prev, [r.field]: e.target.value }))}
                  size="small"
                >
                  <Radio.Button value="old">保留原值</Radio.Button>
                  <Radio.Button value="new">采用新值</Radio.Button>
                </Radio.Group>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
};

export default CompanyDetail;
