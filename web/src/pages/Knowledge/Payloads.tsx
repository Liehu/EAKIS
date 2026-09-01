import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, InputNumber, Tag, message, Space, Tabs, Drawer } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { getPayloads, createPayload, updatePayload, deletePayload, recordPayloadHit } from '@/api/knowledge';
import type { Payload, PayloadCategory } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';

const categoryLabel: Record<PayloadCategory, string> = {
  pass: '密码字典', path: '路径字典', user: '用户名字典', header: '请求头', payload: '攻击载荷', keywords: '关键词库',
};

// 分类语义令牌（规范 §06 标签：10% 同色底 + 同色字）——按原色相意图映射：
// pass=error红 · path=accent蓝 · user=high橙 · header=low青绿 · payload=warning黄 · keywords=success绿
const CATEGORY_TOKENS: Record<PayloadCategory, string> = {
  pass: 'var(--error)', path: 'var(--accent-color)', user: 'var(--severity-high)',
  header: 'var(--severity-low)', payload: 'var(--warning)', keywords: 'var(--success)',
};

// 分类标签：10% 同色底 + 同色字（形态对齐 .severity-badge：4px 12px / r12 / 12px）
const CategoryTag: React.FC<{ cat: PayloadCategory }> = ({ cat }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: CATEGORY_TOKENS[cat], background: 'color-mix(in srgb, currentColor 10%, transparent)',
  }}>{categoryLabel[cat]}</span>
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

const PayloadsPage: React.FC = () => {
  const [category, setCategory] = useState<PayloadCategory>('pass');
  const [items, setItems] = useState<Payload[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Payload | null>(null);
  const [form] = Form.useForm();

  const [detail, setDetail] = useState<Payload | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const fetchItems = async (p = page) => {
    setLoading(true);
    try {
      const res = await getPayloads({ page: p, page_size: 20, category, q: q || undefined });
      setItems(res.data);
      setTotal(res.pagination.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchItems(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, q]);

  useEffect(() => {
    fetchItems(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ category, weight: 1.0 });
    setModalOpen(true);
  };

  const openEdit = (p: Payload) => {
    setEditing(p);
    form.setFieldsValue(p);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updatePayload(editing.id, values);
        message.success('已更新');
      } else {
        await createPayload(values);
        message.success('已创建');
      }
      setModalOpen(false);
      fetchItems();
    } catch {
      message.error('操作失败');
    }
  };

  const handleHit = async (p: Payload) => {
    try {
      const updated = await recordPayloadHit(p.id);
      message.success(`命中次数: ${updated.hit_count}`);
      fetchItems();
      if (detail?.id === p.id) setDetail(updated);
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = (p: Payload) => {
    Modal.confirm({
      title: `删除 "${p.name || p.content.slice(0, 20)}"?`,
      okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        try {
          await deletePayload(p.id);
          message.success('已删除');
          fetchItems();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const content = (cat: PayloadCategory) => (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{categoryLabel[cat]}</span>
        <Space>
          <Input.Search placeholder="搜索名称/内容" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Button type="primary" size="small" onClick={openCreate}>新增</Button>
        </Space>
      </div>
      <Table
        size="small" loading={loading} dataSource={items} rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        onRow={(r) => ({ onClick: () => { setDetail(r); setDrawerOpen(true); setPanelItem('knowledge', r as unknown as Record<string, unknown>, 'payload'); }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '名称', dataIndex: 'name', key: 'name', width: 160, render: (v: string) => v || '—' },
          {
            title: '内容预览', dataIndex: 'content', key: 'content', ellipsis: true,
            render: (v: string) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{v?.replace(/\n/g, ' | ').slice(0, 60)}</span>,
          },
          { title: '分组', dataIndex: 'group_name', key: 'group', width: 110, render: (v: string) => v ? <Tag>{v}</Tag> : '—' },
          { title: '权重', dataIndex: 'weight', key: 'weight', width: 80, sorter: true },
          { title: '命中', dataIndex: 'hit_count', key: 'hit', width: 80, render: (v: number) => v || 0 },
          {
            // 行操作统一 type=link size=small（规范 §02 表格页）
            title: '操作', key: 'action', width: 200,
            render: (_, r) => (
              <Space size="small" onClick={(e) => e.stopPropagation()}>
                <Button type="link" size="small" onClick={() => handleHit(r)}>记录命中</Button>
                <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
                <Button type="link" size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />
    </>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">Payload 库</span>
      </div>
      <div className="eakis-page-content">
        <Tabs
          activeKey={category}
          onChange={(k) => setCategory(k as PayloadCategory)}
          items={(Object.keys(categoryLabel) as PayloadCategory[]).map((c) => ({
            key: c, label: <CategoryTag cat={c} />,
          }))}
        />
        {content(category)}
      </div>

      <Modal
        title={editing ? `编辑: ${editing.name || '项'}` : `新增${categoryLabel[category]}项`}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit}
        okText="保存" cancelText="取消" width={560} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称 (可选)">
            <Input />
          </Form.Item>
          <Form.Item name="category" label="类型" rules={[{ required: true }]}>
            <Select options={(Object.keys(categoryLabel) as PayloadCategory[]).map((c) => ({ value: c, label: categoryLabel[c] }))} />
          </Form.Item>
          <Form.Item name="group_name" label="分组">
            <Input placeholder="常见弱口令 / 敏感路径 / ua 等" />
          </Form.Item>
          <Form.Item name="content" label="内容 (支持多行换行)" rules={[{ required: true }]}>
            <Input.TextArea rows={6} placeholder="每行一个词，或一个多行项" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="weight" label="权重 (排序用)" tooltip="数值越大越优先">
            <InputNumber min={0} step={0.1} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="字典项详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={480}>
        {detail && (
          <>
            <p><strong>名称:</strong> {detail.name || '—'}</p>
            <p><strong>类型:</strong> <CategoryTag cat={detail.category} /></p>
            <p><strong>分组:</strong> {detail.group_name || '—'}</p>
            <p><strong>权重:</strong> {detail.weight} | <strong>命中:</strong> {detail.hit_count}</p>
            <p><strong>描述:</strong> {detail.description || '—'}</p>
            <div style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>内容</span>
                <CopyButton text={detail.content} />
              </div>
              <pre style={codeBlockStyle}>{detail.content}</pre>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default PayloadsPage;
