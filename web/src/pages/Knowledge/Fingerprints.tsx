import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Drawer, Descriptions } from 'antd';
import { getFingerprints, createFingerprint, updateFingerprint, deleteFingerprint } from '@/api/knowledge';
import type { Fingerprint } from '@/types/knowledge';
import { useRightPanelStore } from '@/store/rightPanelStore';

const statusColor: Record<string, string> = { draft: 'default', pending_review: 'processing', published: 'success', deprecated: 'error' };
const statusLabel: Record<string, string> = { draft: '草稿', pending_review: '待审核', published: '已发布', deprecated: '已弃用' };

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
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>指纹库</span>
        <Space>
          <Input.Search placeholder="搜索名称/组件" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>
        </Space>
      </div>
      <Table size="small" loading={loading} dataSource={items} rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        onRow={(r) => ({ onClick: () => { setDetail(r); setPanelItem('knowledge', r as unknown as Record<string, unknown>, 'fingerprint'); }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
          { title: '组件', dataIndex: 'component', key: 'component', width: 120 },
          { title: '版本', dataIndex: 'version', key: 'version', width: 90, render: (v: string) => v || '—' },
          { title: '分类', dataIndex: 'category', key: 'category', width: 90, render: (v: string) => v ? <Tag>{v}</Tag> : '—' },
          { title: '匹配方式', dataIndex: 'match_type', key: 'match', width: 90 },
          { title: '关联漏洞', dataIndex: 'vuln_count', key: 'vuln_count', width: 90, render: (v: number) => v || 0 },
          { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColor[v]}>{statusLabel[v]}</Tag> },
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
          <Form.Item name="match_rule" label="匹配规则" rules={[{ required: true }]}><Input.TextArea rows={3} placeholder="正则/字符串/hash" /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="指纹详情" open={!!detail} onClose={() => setDetail(null)} width={440}>
        {detail && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
            <Descriptions.Item label="组件/版本">{[detail.component, detail.version].filter(Boolean).join(' / ') || '—'}</Descriptions.Item>
            <Descriptions.Item label="分类">{detail.category || '—'}</Descriptions.Item>
            <Descriptions.Item label="匹配方式">{detail.match_type || '—'}</Descriptions.Item>
            <Descriptions.Item label="匹配规则"><pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{detail.match_rule}</pre></Descriptions.Item>
            <Descriptions.Item label="关联漏洞">{detail.vuln_count}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColor[detail.status]}>{statusLabel[detail.status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="描述">{detail.description || '—'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default FingerprintPage;
