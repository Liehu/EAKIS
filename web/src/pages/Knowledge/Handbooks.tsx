import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer } from 'antd';
import { getHandbooks, createHandbook, updateHandbook, deleteHandbook } from '@/api/knowledge';
import type { Handbook } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';

const statusColor: Record<string, string> = { draft: 'default', pending_review: 'processing', published: 'success', deprecated: 'error' };
const statusLabel: Record<string, string> = { draft: '草稿', pending_review: '待审核', published: '已发布', deprecated: '已弃用' };

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
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>攻防经验手册</span>
        <Space>
          <Input.Search placeholder="搜索标题/内容" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>
        </Space>
      </div>
      <Table size="small" loading={loading} dataSource={items} rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        onRow={(r) => ({ onClick: () => { setDetail(r); setDrawerOpen(true); setPanelItem('knowledge', r as unknown as Record<string, unknown>, 'handbook'); }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
          { title: '分类', dataIndex: 'category', key: 'category', width: 120, render: (v: string) => v ? <Tag>{v}</Tag> : '—' },
          { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true, render: (v: string) => v || '—' },
          { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColor[v]}>{statusLabel[v]}</Tag> },
          { title: '贡献者', dataIndex: 'contributed_by', key: 'contributor', width: 120, render: (v: string) => v || '—' },
          {
            title: '操作', key: 'action', width: 140,
            render: (_, r) => (
              <Space size="small" onClick={(e) => e.stopPropagation()}>
                <Button size="small" onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? `编辑: ${editing.title}` : '新增手册'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={640}>
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类">
            <Select allowClear options={[{ value: '攻击案例', label: '攻击案例' }, { value: '防御方案', label: '防御方案' }, { value: '应急响应', label: '应急响应' }]} />
          </Form.Item>
          <Form.Item name="summary" label="摘要"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="content" label="正文 (Markdown)" rules={[{ required: true }]}>
            <Input.TextArea rows={8} style={{ fontFamily: 'monospace' }} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer title={detail?.title} open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560}>
        {detail && (
          <>
            <p><strong>分类:</strong> <Tag>{detail.category || '—'}</Tag> <strong>状态:</strong> <Tag color={statusColor[detail.status]}>{statusLabel[detail.status]}</Tag></p>
            {detail.summary && <p><strong>摘要:</strong> {detail.summary}</p>}
            <div style={{ marginTop: 12 }}>
              <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>正文</div>
              <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{detail.content}</pre>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default HandbookPage;
