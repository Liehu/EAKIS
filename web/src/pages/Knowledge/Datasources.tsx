import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space } from 'antd';
import { getDatasources, createDatasource, updateDatasource, deleteDatasource } from '@/api/knowledge';
import type { Datasource } from '@/types/knowledge';

const DatasourcePage: React.FC = () => {
  const [items, setItems] = useState<Datasource[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Datasource | null>(null);
  const [form] = Form.useForm();

  const fetchItems = async (p = page) => {
    setLoading(true);
    try {
      const res = await getDatasources({ page: p, page_size: 20 });
      setItems(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchItems(page); }, [page]); // eslint-disable-line

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) { await updateDatasource(editing.id, values); message.success('已更新'); }
      else { await createDatasource(values); message.success('已创建'); }
      setModalOpen(false); fetchItems();
    } catch { message.error('操作失败'); }
  };

  const handleDelete = (d: Datasource) => {
    Modal.confirm({
      title: `删除数据源 "${d.name}"?`, okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => { try { await deleteDatasource(d.id); message.success('已删除'); fetchItems(); } catch { message.error('失败'); } },
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>数据源定义</span>
        <Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>
      </div>
      <Table size="small" loading={loading} dataSource={items} rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        columns={[
          { title: '名称', dataIndex: 'name', key: 'name' },
          { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (v: string) => <Tag color="blue">{v}</Tag> },
          { title: 'API 地址', dataIndex: 'api_base_url', key: 'url', ellipsis: true, render: (v: string) => v || '—' },
          { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true, render: (v: string) => v || '—' },
          { title: '启用', dataIndex: 'is_active', key: 'active', width: 70, render: (v: number) => <Tag color={v ? 'green' : 'default'}>{v ? '是' : '否'}</Tag> },
          {
            title: '操作', key: 'action', width: 140,
            render: (_, r) => (
              <Space size="small">
                <Button size="small" onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? `编辑: ${editing.name}` : '新增数据源'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={520}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
            <Select options={[{ value: 'fofa', label: 'Fofa' }, { value: 'shodan', label: 'Shodan' }, { value: 'hunter', label: 'Hunter' }, { value: 'quake', label: 'Quake' }, { value: 'zoomeye', label: 'ZoomEye' }]} />
          </Form.Item>
          <Form.Item name="api_base_url" label="API 地址"><Input placeholder="https://api.xxx.com" /></Form.Item>
          <Form.Item name="config" label="配置 (JSON)"><Input.TextArea rows={4} placeholder='{"fields":[],"page_size":100}' style={{ fontFamily: 'monospace' }} /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DatasourcePage;
