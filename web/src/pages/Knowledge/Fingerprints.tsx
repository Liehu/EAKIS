import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer, Descriptions } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { getFingerprints, createFingerprint, updateFingerprint, deleteFingerprint } from '@/api/knowledge';
import type { Fingerprint } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';
import FilterBar from '@/components/FilterBar';

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

// 分类/平台标签（语义令牌）：accent 8% 底 + accent 字，999px 胶囊（规范 §05 圆角胶囊）
const TokenTag: React.FC<{ text: string }> = ({ text }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: 'var(--accent-color)', background: 'var(--accent-alpha-08)',
  }}>{text}</span>
);

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

const FingerprintPage: React.FC = () => {
  const [items, setItems] = useState<Fingerprint[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Fingerprint | null>(null);
  const [form] = Form.useForm();
  const [detail, setDetail] = useState<Fingerprint | null>(null);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const fetchItems = async (p = page) => {
    setLoading(true);
    try {
      const res = await getFingerprints({ page: p, page_size: 20, q: q || undefined });
      setItems(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchItems(page); }, [page, q]); // eslint-disable-line

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) { await updateFingerprint(editing.id, values); message.success('已更新'); }
      else { await createFingerprint(values); message.success('已创建 (草稿)'); }
      setModalOpen(false); fetchItems();
    } catch { message.error('操作失败'); }
  };

  const handleDelete = (f: Fingerprint) => {
    Modal.confirm({
      title: `删除指纹 "${f.name}"?`, okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => { try { await deleteFingerprint(f.id); message.success('已删除'); fetchItems(); } catch { message.error('失败'); } },
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">指纹库</span>
        <FilterBar
          searchPlaceholder="搜索名称/组件"
          onSearch={setQ}
          extra={<Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>}
        />
      </div>
      <div className="eakis-page-content">
        <Table size="small" loading={loading} dataSource={items} rowKey="id"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
          onRow={(r) => ({ onClick: () => { setDetail(r); setPanelItem('knowledge', r as unknown as Record<string, unknown>, 'fingerprint'); }, style: { cursor: 'pointer' } })}
          columns={[
            { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
            { title: '组件', dataIndex: 'component', key: 'component', width: 120 },
            { title: '版本', dataIndex: 'version', key: 'version', width: 90, render: (v: string) => v || '—' },
            { title: '分类', dataIndex: 'category', key: 'category', width: 100, render: (v: string) => v ? <TokenTag text={v} /> : '—' },
            { title: '匹配方式', dataIndex: 'match_type', key: 'match', width: 90 },
            { title: '关联漏洞', dataIndex: 'vuln_count', key: 'vuln_count', width: 90, render: (v: number) => v || 0 },
            { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <KnowledgeStatusBadge status={v} /> },
            {
              // 行操作统一 type=link size=small（规范 §02 表格页）
              title: '操作', key: 'action', width: 140,
              render: (_, r) => (
                <Space size="small" onClick={(e) => e.stopPropagation()}>
                  <Button type="link" size="small" onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                  <Button type="link" size="small" danger onClick={() => handleDelete(r)}>删除</Button>
                </Space>
              ),
            },
          ]}
        />
      </div>
      <Modal title={editing ? `编辑: ${editing.name}` : '新增指纹'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="component" label="组件" style={{ width: 180 }}><Input placeholder="Nginx/Apache/Spring" /></Form.Item>
            <Form.Item name="version" label="版本" style={{ width: 150 }}><Input placeholder="1.x" /></Form.Item>
            <Form.Item name="category" label="分类" style={{ width: 150 }}>
              <Select allowClear options={[{ value: 'web', label: 'Web' }, { value: 'framework', label: '框架' }, { value: 'service', label: '服务' }, { value: 'os', label: 'OS' }]} />
            </Form.Item>
          </Space>
          <Form.Item name="match_type" label="匹配方式">
            <Select allowClear options={[{ value: 'header', label: 'Header' }, { value: 'body', label: 'Body' }, { value: 'favicon', label: 'Favicon' }, { value: 'cookie', label: 'Cookie' }]} />
          </Form.Item>
          <Form.Item name="match_rule" label="匹配规则" rules={[{ required: true }]}><Input.TextArea rows={3} placeholder="正则/字符串/hash" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="指纹详情" open={!!detail} onClose={() => setDetail(null)} width={440}>
        {detail && (
          <Descriptions column={1} size="small" bordered
            labelStyle={{ background: 'var(--bg-thead)', color: 'var(--text-secondary)', width: 90 }}
            contentStyle={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
            <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
            <Descriptions.Item label="组件/版本">{[detail.component, detail.version].filter(Boolean).join(' / ') || '—'}</Descriptions.Item>
            <Descriptions.Item label="分类">{detail.category || '—'}</Descriptions.Item>
            <Descriptions.Item label="匹配方式">{detail.match_type || '—'}</Descriptions.Item>
            <Descriptions.Item label="匹配规则">
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
                  <CopyButton text={detail.match_rule} />
                </div>
                <pre style={codeBlockStyle}>{detail.match_rule}</pre>
              </div>
            </Descriptions.Item>
            <Descriptions.Item label="关联漏洞">{detail.vuln_count}</Descriptions.Item>
            <Descriptions.Item label="状态"><KnowledgeStatusBadge status={detail.status} /></Descriptions.Item>
            <Descriptions.Item label="描述">{detail.description || '—'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default FingerprintPage;
