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

const industryLabels: Record<string, string> = {
  fintech: '金融科技', ecommerce: '电商', tech: '互联网',
  government: '政务', healthcare: '医疗', security: '安全服务',
  cloud: '云计算', data_security: '数据安全', research: '安全研究',
  telecom: '通信', education: '教育', energy: '能源',
  logistics: '物流', gaming: '游戏', iot: '物联网',
  edtech: '教育科技', ai: '人工智能', cold_chain: '冷链',
  express: '快递', warehouse: '仓储', hardware: '硬件',
};

const statusLabels: Record<string, { text: string; color: string }> = {
  active: { text: '活跃', color: 'green' },
  inactive: { text: '停用', color: 'default' },
  archived: { text: '归档', color: 'orange' },
};

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
          <a onClick={() => onSelectCompany(record.id)} style={{ color: '#378ADD', cursor: 'pointer' }}>{text}</a>
        ) : text,
    },
    { title: '全称', dataIndex: 'full_name', key: 'full_name', ellipsis: true, width: 180 },
    { title: '信用代码', dataIndex: 'credit_code', key: 'credit_code', width: 160, ellipsis: true },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 90, render: (v: string) => <Tag>{industryLabels[v] || v}</Tag> },
    { title: '关键词', dataIndex: 'keywords', key: 'keywords', width: 160, render: (v: string[]) => v?.map((k) => <Tag key={k}>{k}</Tag>) || '-' },
    { title: '域名', dataIndex: 'domains', key: 'domains', width: 140, render: (v: string[]) => v?.join(', ') || '-' },
    { title: '官网', dataIndex: 'website', key: 'website', width: 120, ellipsis: true, render: (v: string) => v ? <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: '#378ADD' }}>{v.replace(/^https?:\/\//, '')}</a> : '-' },
    { title: '法人', dataIndex: 'legal_person', key: 'legal_person', width: 70 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 60, render: (v: string) => { const s = statusLabels[v]; return s ? <Tag color={s.color}>{s.text}</Tag> : <Tag>{v}</Tag>; } },
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
    { title: '状态', dataIndex: 'status', key: 'status', width: 70, render: (v: string) => <Tag color={v === 'confirmed' ? 'green' : v === 'false_positive' ? 'default' : 'blue'}>{v}</Tag> },
    { title: '发现时间', dataIndex: 'discovered_at', key: 'discovered_at', width: 110, render: (v: string) => v?.slice(0, 10) },
  ];

  const renderVulnCount = (vc: { critical: number; high: number; medium: number; low: number }, assetId: string) => {
    const total = vc.critical + vc.high + vc.medium + vc.low;
    if (total === 0) return <span style={{ color: '#666' }}>0</span>;
    return (
      <a
        onClick={(e) => { e.stopPropagation(); handleVulnCountClick(assetId); }}
        style={{ color: '#378ADD', cursor: 'pointer' }}
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
        <Descriptions
          bordered
          size="small"
          column={2}
          colon={false}
          labelStyle={{ background: '#141422', color: '#888', fontWeight: 400, padding: '10px 16px', whiteSpace: 'nowrap' }}
          contentStyle={{ background: '#1a1a2e', color: '#e2e8f0', padding: '10px 16px' }}
          style={{ maxWidth: 960 }}
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
              { label: 'IP', count: assetSummary.by_type.ip || 0, color: '#378ADD' },
              { label: '域名', count: assetSummary.by_type.domain || 0, color: '#639922' },
              { label: 'Web', count: assetSummary.by_type.web || 0, color: '#BA7517' },
              { label: 'APP', count: assetSummary.by_type.app || 0, color: '#534AB7' },
              { label: '小程序', count: assetSummary.by_type.miniprogram || 0, color: '#888' },
            ].map((item) => (
              <div key={item.label} style={{ background: '#141422', border: '1px solid #2a2a4e', borderRadius: 6, padding: '8px 16px', minWidth: 80, textAlign: 'center' }}>
                <div style={{ color: '#888', fontSize: 12 }}>{item.label}</div>
                <div style={{ color: item.color, fontSize: 18, fontWeight: 500 }}>{item.count}</div>
              </div>
            ))}
          </div>
          <Table size="small" dataSource={companyAssetsList}
            rowKey="_rowKey" pagination={false}
            columns={[
              { title: '类型', dataIndex: '_category', key: 'cat', width: 60, render: (v: string) => <Tag>{v}</Tag> },
              { title: '标识', key: 'identifier', ellipsis: true, render: (_: any, r: any) => r.ip_address || r.domain || r.url || r.name || '-' },
              { title: '关联单位', dataIndex: 'related_units', key: 'units', width: 150, render: (v: string[]) => v?.join(', ') || '-' },
              { title: '风险', dataIndex: 'risk_level', key: 'risk', width: 60, render: (v: string) => <RiskTag level={v as any} /> },
              { title: '漏洞数', key: 'vuln', width: 60, render: (_: any, r: any) => renderVulnCount(r.vuln_count, r.id) },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'risks',
      label: `企业风险 (${totalVulns})`,
      children: (
        <Table size="small" dataSource={vulnData} rowKey="id" pagination={false} columns={vulnColumns} />
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
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button size="small" icon={<ArrowLeftOutlined />} onClick={onBack}>返回列表</Button>
        <span style={{ color: '#e2e8f0', fontSize: 16, fontWeight: 500 }}>{detail.name}</span>
        {detail.business_status && <Tag>{detail.business_status}</Tag>}
        <span style={{ color: '#888', fontSize: 12, marginLeft: 8 }}>
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
      <Tabs defaultActiveKey="info" items={tabItems} style={{ color: '#e2e8f0' }} />

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
        <p style={{ color: '#888', marginBottom: 16 }}>
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
                  ? <span style={{ color: '#666' }}>(空)</span>
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
                <span style={{ color: '#888', fontSize: 12 }}>
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
