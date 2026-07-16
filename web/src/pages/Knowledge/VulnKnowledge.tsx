import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer, Descriptions } from 'antd';
import { getVulns, createVuln, updateVuln, deleteVuln, reviewVuln, getFingerprints } from '@/api/knowledge';
import type { VulnKnowledge, Fingerprint } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';

const severityColor: Record<string, string> = {
  critical: 'red', high: 'orange', medium: 'gold', low: 'blue', info: 'default',
};
const severityLabel: Record<string, string> = {
  critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息',
};
const statusColor: Record<string, string> = {
  draft: 'default', pending_review: 'processing', published: 'success', deprecated: 'error',
};
const statusLabel: Record<string, string> = {
  draft: '草稿', pending_review: '待审核', published: '已发布', deprecated: '已弃用',
};

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

  const reviewActions = (v: VulnKnowledge) => {
    const btns: React.ReactNode[] = [];
    if (v.status === 'draft') btns.push(<Button size="small" onClick={() => handleReview(v, 'submit')}>提交审核</Button>);
    if (v.status === 'pending_review') {
      btns.push(<Button size="small" type="primary" onClick={() => handleReview(v, 'approve')}>通过</Button>);
      btns.push(<Button size="small" danger onClick={() => handleReview(v, 'reject')}>驳回</Button>);
    }
    if (v.status === 'published') btns.push(<Button size="small" danger onClick={() => handleReview(v, 'deprecate')}>弃用</Button>);
    return <Space size="small">{btns}</Space>;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>漏洞知识库</span>
        <Space>
          <Select placeholder="严重度" allowClear size="small" style={{ width: 100 }}
            value={filters.severity} onChange={(v) => setFilters({ ...filters, severity: v })}
            options={Object.entries(severityLabel).map(([k, l]) => ({ value: k, label: l }))} />
          <Select placeholder="状态" allowClear size="small" style={{ width: 110 }}
            value={filters.status} onChange={(v) => setFilters({ ...filters, status: v })}
            options={Object.entries(statusLabel).map(([k, l]) => ({ value: k, label: l }))} />
          <Input.Search placeholder="名称/编号/厂商" allowClear size="small" style={{ width: 180 }}
            onSearch={(v) => setFilters({ ...filters, q: v })} />
          <Button type="primary" size="small" onClick={openCreate}>新增</Button>
        </Space>
      </div>

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
            title: '严重度', dataIndex: 'severity', key: 'severity', width: 80,
            render: (v: string) => <Tag color={severityColor[v]}>{severityLabel[v]}</Tag>,
          },
          {
            title: '状态', dataIndex: 'status', key: 'status', width: 90,
            render: (v: string) => <Tag color={statusColor[v]}>{statusLabel[v]}</Tag>,
          },
          { title: '标签', dataIndex: 'tags', key: 'tags', width: 140, render: (t: string[]) => t?.map((x) => <Tag key={x}>{x}</Tag>) || '—' },
          {
            title: '操作', key: 'action', width: 220,
            render: (_, r) => (
              <Space size="small" onClick={(e) => e.stopPropagation()}>
                {reviewActions(r)}
                <Button size="small" onClick={() => openEdit(r)}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />

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
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="编号">{detail.vuln_id || '—'}</Descriptions.Item>
              <Descriptions.Item label="类型">{detail.vuln_type || '—'}</Descriptions.Item>
              <Descriptions.Item label="严重度"><Tag color={severityColor[detail.severity]}>{severityLabel[detail.severity]}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor[detail.status]}>{statusLabel[detail.status]}</Tag></Descriptions.Item>
              <Descriptions.Item label="厂商/产品">{[detail.vendor, detail.product].filter(Boolean).join(' / ') || '—'}</Descriptions.Item>
              <Descriptions.Item label="影响版本">{detail.version_range || '—'}</Descriptions.Item>
              <Descriptions.Item label="影响范围">{detail.affected_scope || '—'}</Descriptions.Item>
              <Descriptions.Item label="贡献者">{detail.contributed_by || '—'}</Descriptions.Item>
              <Descriptions.Item label="审核人">{detail.reviewed_by || '—'}</Descriptions.Item>
              <Descriptions.Item label="标签">{detail.tags?.length ? detail.tags.map((t) => <Tag key={t}>{t}</Tag>) : '—'}</Descriptions.Item>
            </Descriptions>
            {detail.poc && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>POC/Payload</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{detail.poc}</pre>
              </div>
            )}
            {detail.remediation && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>修复方案</div>
                <div style={{ color: '#cbd5e1' }}>{detail.remediation}</div>
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
