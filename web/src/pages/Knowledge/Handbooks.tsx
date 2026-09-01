import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { getHandbooks, createHandbook, updateHandbook, deleteHandbook } from '@/api/knowledge';
import type { Handbook } from '@/types/knowledge';
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

// 分类标签（语义令牌）：accent 8% 底 + accent 字，999px 胶囊（规范 §05 圆角胶囊）
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

const HandbookPage: React.FC = () => {
  const [items, setItems] = useState<Handbook[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Handbook | null>(null);
  const [form] = Form.useForm();
  const [detail, setDetail] = useState<Handbook | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const fetchItems = async (p = page) => {
    setLoading(true);
    try {
      const res = await getHandbooks({ page: p, page_size: 20, q: q || undefined });
      setItems(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchItems(page); }, [page, q]); // eslint-disable-line

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) { await updateHandbook(editing.id, values); message.success('已更新'); }
      else { await createHandbook(values); message.success('已创建 (草稿)'); }
      setModalOpen(false); fetchItems();
    } catch { message.error('操作失败'); }
  };

  const handleDelete = (h: Handbook) => {
    Modal.confirm({
      title: `删除手册 "${h.title}"?`, okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => { try { await deleteHandbook(h.id); message.success('已删除'); fetchItems(); } catch { message.error('失败'); } },
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">攻防经验手册</span>
        <FilterBar
          searchPlaceholder="搜索标题/内容"
          onSearch={setQ}
          extra={<Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>}
        />
      </div>
      <div className="eakis-page-content">
        <Table size="small" loading={loading} dataSource={items} rowKey="id"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
          onRow={(r) => ({ onClick: () => { setDetail(r); setDrawerOpen(true); setPanelItem('knowledge', r as unknown as Record<string, unknown>, 'handbook'); }, style: { cursor: 'pointer' } })}
          columns={[
            { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
            { title: '分类', dataIndex: 'category', key: 'category', width: 130, render: (v: string) => v ? <TokenTag text={v} /> : '—' },
            { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true, render: (v: string) => v || '—' },
            { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <KnowledgeStatusBadge status={v} /> },
            { title: '贡献者', dataIndex: 'contributed_by', key: 'contributor', width: 120, render: (v: string) => v || '—' },
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
      <Modal title={editing ? `编辑: ${editing.title}` : '新增手册'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={640}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类">
            <Select allowClear options={[{ value: '攻击案例', label: '攻击案例' }, { value: '防御方案', label: '防御方案' }, { value: '应急响应', label: '应急响应' }]} />
          </Form.Item>
          <Form.Item name="summary" label="摘要"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="content" label="正文 (Markdown)" rules={[{ required: true }]}>
            <Input.TextArea rows={8} style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer title={detail?.title} open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560}>
        {detail && (
          // 手册卡：.eakis-panel 卡壳（r8 + 1px 描边，规范 §06）
          <div className="eakis-panel" style={{ padding: 16 }}>
            <p style={{ margin: '0 0 8px' }}>
              <strong>分类:</strong> {detail.category ? <TokenTag text={detail.category} /> : '—'} <strong>状态:</strong> <KnowledgeStatusBadge status={detail.status} />
            </p>
            {detail.summary && <p style={{ margin: '0 0 12px', color: 'var(--text-secondary)' }}><strong>摘要:</strong> {detail.summary}</p>}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>正文</span>
              <CopyButton text={detail.content} />
            </div>
            <pre style={codeBlockStyle}>{detail.content}</pre>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default HandbookPage;
