import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer, Descriptions } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { getVulns, createVuln, updateVuln, deleteVuln, reviewVuln, getFingerprints } from '@/api/knowledge';
import type { VulnKnowledge, Fingerprint } from '@/types/knowledge';
import type { RiskLevel } from '@/types/asset';
import { useRightPanelStore } from '@/store/rightPanelStore';
import RiskTag from '@/components/RiskTag';
import FilterBar from '@/components/FilterBar';

const severityLabel: Record<string, string> = {
  critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息',
};

// 知识状态语义令牌（规范 §06 状态徽章：10% 同色底 + 同色字 / 500 字重）
// draft=中性 · pending_review=accent（流转中）· published=success · deprecated=弱化
const STATUS_TOKENS: Record<string, { label: string; token: string }> = {
  draft: { label: '草稿', token: 'var(--text-secondary)' },
  pending_review: { label: '待审核', token: 'var(--accent-color)' },
  published: { label: '已发布', token: 'var(--success)' },
  deprecated: { label: '已弃用', token: 'var(--text-muted)' },
};

// 状态徽章：10% 同色底 + 同色字（形态对齐 .severity-badge：4px 12px / r12 / 12px）
const KnowledgeStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg = STATUS_TOKENS[status];
  if (!cfg) return <Tag>{status}</Tag>;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
      lineHeight: 1.2, whiteSpace: 'nowrap',
      color: cfg.token, background: 'color-mix(in srgb, currentColor 10%, transparent)',
    }}>{cfg.label}</span>
  );
};

// 代码块规范：bg-secondary + 1px var(--border-color) + r6 + mono 12px/1.5（规范 §05/§06）
const codeBlockStyle: React.CSSProperties = {
  margin: 0,
  padding: 12,
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-sm)',
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  lineHeight: 1.5,
  color: 'var(--text-primary)',
  overflow: 'auto',
  whiteSpace: 'pre-wrap',
};

// 代码块复制按钮（type=text size=small）
const CopyButton: React.FC<{ text: string }> = ({ text }) => (
  <Button
    type="text"
    size="small"
    icon={<CopyOutlined />}
    onClick={(e) => {
      e.stopPropagation();
      navigator.clipboard?.writeText(text)
        .then(() => message.success('已复制'))
        .catch(() => message.error('复制失败'));
    }}
  />
);

const VulnKnowledgePage: React.FC = () => {
  const [vulns, setVulns] = useState<VulnKnowledge[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<{ severity?: string; status?: string; q?: string }>({});

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<VulnKnowledge | null>(null);
  const [form] = Form.useForm();
  const [fingerprints, setFingerprints] = useState<Fingerprint[]>([]);

  const [detail, setDetail] = useState<VulnKnowledge | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const fetchVulns = async (p = page) => {
    setLoading(true);
    try {
      const res = await getVulns({ page: p, page_size: 20, ...filters });
      setVulns(res.data);
      setTotal(res.pagination.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVulns(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filters]);

  const openCreate = async () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ severity: 'medium' });
    // load fingerprints for association
    const fpRes = await getFingerprints({ page: 1, page_size: 100 });
    setFingerprints(fpRes.data);
    setModalOpen(true);
  };

  const openEdit = async (v: VulnKnowledge) => {
    setEditing(v);
    const fpRes = await getFingerprints({ page: 1, page_size: 100 });
    setFingerprints(fpRes.data);
    form.setFieldsValue(v);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updateVuln(editing.id, values);
        message.success('已更新');
      } else {
        await createVuln(values);
        message.success('已创建 (草稿状态)');
      }
      setModalOpen(false);
      fetchVulns();
    } catch {
      message.error('操作失败');
    }
  };

  const handleReview = async (v: VulnKnowledge, action: 'submit' | 'approve' | 'reject' | 'deprecate') => {
    const labels = { submit: '提交审核', approve: '通过', reject: '驳回', deprecate: '弃用' };
    try {
      await reviewVuln(v.id, { action });
      message.success(labels[action]);
      fetchVulns();
      if (detail?.id === v.id) setDetail({ ...v, status: action === 'submit' ? 'pending_review' : action === 'approve' ? 'published' : action === 'reject' ? 'draft' : 'deprecated' });
    } catch (e: any) {
      message.error(e.response?.data?.detail || '审核操作失败');
    }
  };

  const handleDelete = (v: VulnKnowledge) => {
    Modal.confirm({
      title: `删除漏洞知识 "${v.name}"?`,
      okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        try {
          await deleteVuln(v.id);
          message.success('已删除');
          fetchVulns();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const openDetail = (v: VulnKnowledge) => {
    setDetail(v);
    setDrawerOpen(true);
    setPanelItem('knowledge', v as unknown as Record<string, unknown>, 'vuln');
  };

  // 行操作统一 type=link size=small（规范 §02 表格页）
  const reviewActions = (v: VulnKnowledge) => {
    const btns: React.ReactNode[] = [];
    if (v.status === 'draft') btns.push(<Button key="submit" type="link" size="small" onClick={() => handleReview(v, 'submit')}>提交审核</Button>);
    if (v.status === 'pending_review') {
      btns.push(<Button key="approve" type="link" size="small" onClick={() => handleReview(v, 'approve')}>通过</Button>);
      btns.push(<Button key="reject" type="link" size="small" danger onClick={() => handleReview(v, 'reject')}>驳回</Button>);
    }
    if (v.status === 'published') btns.push(<Button key="deprecate" type="link" size="small" danger onClick={() => handleReview(v, 'deprecate')}>弃用</Button>);
    return <Space size="small">{btns}</Space>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">漏洞知识库</span>
        <FilterBar
          searchPlaceholder="名称/编号/厂商"
          onSearch={(v) => setFilters({ ...filters, q: v })}
          filters={[
            {
              key: 'severity',
              label: '严重度',
              value: filters.severity,
              onChange: (v) => setFilters({ ...filters, severity: v }),
              options: Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l })),
            },
            {
              key: 'status',
              label: '状态',
              value: filters.status,
              onChange: (v) => setFilters({ ...filters, status: v }),
              options: Object.entries(STATUS_TOKENS).map(([k, v]) => ({ value: k, label: v.label })),
            },
          ]}
          extra={<Button type="primary" size="small" onClick={openCreate}>新增</Button>}
        />
      </div>
      <div className="eakis-page-content">
        <Table
          size="small" loading={loading} dataSource={vulns} rowKey="id"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
          onRow={(r) => ({ onClick: () => openDetail(r), style: { cursor: 'pointer' } })}
          columns={[
            { title: '漏洞名称', dataIndex: 'name', key: 'name', ellipsis: true },
            { title: '编号', dataIndex: 'vuln_id', key: 'vuln_id', width: 130, render: (v: string) => v || '—' },
            { title: '类型', dataIndex: 'vuln_type', key: 'type', width: 120, render: (v: string) => v || '—' },
            { title: '厂商', dataIndex: 'vendor', key: 'vendor', width: 100, render: (v: string) => v || '—' },
            {
              // 严重度列：全局 .severity-badge + sev-* 五级（中文标签保留，规范 §06）
              title: '严重度', dataIndex: 'severity', key: 'severity', width: 90,
              render: (v: string) => <RiskTag level={v as RiskLevel} />,
            },
            {
              title: '状态', dataIndex: 'status', key: 'status', width: 100,
              render: (v: string) => <KnowledgeStatusBadge status={v} />,
            },
            { title: '标签', dataIndex: 'tags', key: 'tags', width: 140, render: (t: string[]) => t?.map((x) => <Tag key={x}>{x}</Tag>) || '—' },
            {
              title: '操作', key: 'action', width: 220,
              render: (_, r) => (
                <Space size="small" onClick={(e) => e.stopPropagation()}>
                  {reviewActions(r)}
                  <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
                  <Button type="link" size="small" danger onClick={() => handleDelete(r)}>删除</Button>
                </Space>
              ),
            },
          ]}
        />
      </div>

      <Modal
        title={editing ? `编辑: ${editing.name}` : '新增漏洞知识'}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit}
        okText="保存" cancelText="取消" width={640} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="漏洞名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="severity" label="严重度" rules={[{ required: true }]} style={{ width: 130 }}>
              <Select options={Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l }))} />
            </Form.Item>
            <Form.Item name="vuln_id" label="漏洞编号 (CVE/CNVD)" style={{ width: 200 }}>
              <Input placeholder="CVE-2021-41773" />
            </Form.Item>
            <Form.Item name="vuln_type" label="漏洞类型" style={{ width: 200 }}>
              <Input placeholder="SQLi/XSS/SSRF" />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="vendor" label="厂商" style={{ width: 180 }}>
              <Input />
            </Form.Item>
            <Form.Item name="product" label="产品" style={{ width: 180 }}>
              <Input />
            </Form.Item>
            <Form.Item name="version_range" label="影响版本" style={{ width: 180 }}>
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="affected_scope" label="影响范围">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="fingerprint_id" label="关联指纹">
            <Select allowClear placeholder="选择指纹组件" options={fingerprints.map((f) => ({ value: f.id, label: `${f.component || f.name}${f.version ? ' ' + f.version : ''}` }))} />
          </Form.Item>
          <Form.Item name="poc" label="POC/Payload">
            <Input.TextArea rows={4} placeholder="支持多行" />
          </Form.Item>
          <Form.Item name="remediation" label="修复方案">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="漏洞详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560}>
        {detail && (
          <>
            <Descriptions column={1} size="small" bordered
              labelStyle={{ background: 'var(--bg-thead)', color: 'var(--text-secondary)', width: 90 }}
              contentStyle={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
              <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="编号">{detail.vuln_id || '—'}</Descriptions.Item>
              <Descriptions.Item label="类型">{detail.vuln_type || '—'}</Descriptions.Item>
              <Descriptions.Item label="严重度"><RiskTag level={detail.severity} /></Descriptions.Item>
              <Descriptions.Item label="状态"><KnowledgeStatusBadge status={detail.status} /></Descriptions.Item>
              <Descriptions.Item label="厂商/产品">{[detail.vendor, detail.product].filter(Boolean).join(' / ') || '—'}</Descriptions.Item>
              <Descriptions.Item label="影响版本">{detail.version_range || '—'}</Descriptions.Item>
              <Descriptions.Item label="影响范围">{detail.affected_scope || '—'}</Descriptions.Item>
              <Descriptions.Item label="贡献者">{detail.contributed_by || '—'}</Descriptions.Item>
              <Descriptions.Item label="审核人">{detail.reviewed_by || '—'}</Descriptions.Item>
              <Descriptions.Item label="标签">{detail.tags?.length ? detail.tags.map((t) => <Tag key={t}>{t}</Tag>) : '—'}</Descriptions.Item>
            </Descriptions>
            {detail.poc && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>POC/Payload</span>
                  <CopyButton text={detail.poc} />
                </div>
                <pre style={codeBlockStyle}>{detail.poc}</pre>
              </div>
            )}
            {detail.remediation && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: 'var(--text-secondary)', fontSize: 12 }}>修复方案</div>
                <div style={{ color: 'var(--text-secondary)' }}>{detail.remediation}</div>
              </div>
            )}
            <div style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>{reviewActions(detail)}</Space>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default VulnKnowledgePage;
