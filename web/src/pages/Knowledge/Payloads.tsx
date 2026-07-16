import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, InputNumber, Tag, message, Space, Tabs, Drawer } from 'antd';
import { getPayloads, createPayload, updatePayload, deletePayload, recordPayloadHit } from '@/api/knowledge';
import type { Payload, PayloadCategory } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';

const categoryLabel: Record<PayloadCategory, string> = {
  pass: '密码字典', path: '路径字典', user: '用户名字典', header: '请求头', payload: '攻击载荷', keywords: '关键词库',
};
const categoryColor: Record<PayloadCategory, string> = {
  pass: 'red', path: 'blue', user: 'purple', header: 'cyan', payload: 'orange', keywords: 'green',
};

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
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>{categoryLabel[cat]}</span>
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
            render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v?.replace(/\n/g, ' | ').slice(0, 60)}</span>,
          },
          { title: '分组', dataIndex: 'group_name', key: 'group', width: 110, render: (v: string) => v ? <Tag>{v}</Tag> : '—' },
          { title: '权重', dataIndex: 'weight', key: 'weight', width: 80, sorter: true },
          { title: '命中', dataIndex: 'hit_count', key: 'hit', width: 80, render: (v: number) => v || 0 },
          {
            title: '操作', key: 'action', width: 200,
            render: (_, r) => (
              <Space size="small" onClick={(e) => e.stopPropagation()}>
                <Button size="small" onClick={() => handleHit(r)}>记录命中</Button>
                <Button size="small" onClick={() => openEdit(r)}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />
    </>
  );

  return (
    <div>
      <Tabs
        activeKey={category}
        onChange={(k) => setCategory(k as PayloadCategory)}
        items={(Object.keys(categoryLabel) as PayloadCategory[]).map((c) => ({
          key: c, label: <span><Tag color={categoryColor[c]} style={{ marginRight: 4 }}>{categoryLabel[c]}</Tag></span>,
        }))}
      />
      {content(category)}

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
            <Input.TextArea rows={6} placeholder="每行一个词，或一个多行项" style={{ fontFamily: 'monospace' }} />
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
            <p><strong>类型:</strong> <Tag color={categoryColor[detail.category]}>{categoryLabel[detail.category]}</Tag></p>
            <p><strong>分组:</strong> {detail.group_name || '—'}</p>
            <p><strong>权重:</strong> {detail.weight} | <strong>命中:</strong> {detail.hit_count}</p>
            <p><strong>描述:</strong> {detail.description || '—'}</p>
            <div style={{ marginTop: 12 }}>
              <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>内容</div>
              <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{detail.content}</pre>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default PayloadsPage;
