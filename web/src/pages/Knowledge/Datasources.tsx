import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Space } from 'antd';
import { getDatasources, createDatasource, updateDatasource, deleteDatasource } from '@/api/knowledge';
import type { Datasource } from '@/types/knowledge';

// 数据源状态徽章（规范 §06 tool-status 形态：8px 状态点 + 10% 同色底）：
// 在线=success+脉冲点 · 离线=弱化中性 · 错误=error（备用映射，当前数据模型仅 is_active 0/1）
const DsStatusBadge: React.FC<{ active: boolean }> = ({ active }) => {
  const token = active ? 'var(--success)' : 'var(--text-muted)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
      lineHeight: 1.2, whiteSpace: 'nowrap',
      color: token, background: 'color-mix(in srgb, currentColor 10%, transparent)',
    }}>
      <span className={`status-dot${active ? ' is-pulsing' : ''}`} style={{ background: token }} />
      {active ? '在线' : '离线'}
    </span>
  );
};

// 平台标签（语义令牌）：accent 8% 底 + accent 字，999px 胶囊（规范 §05 圆角胶囊）
const TokenTag: React.FC<{ text: string }> = ({ text }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: 'var(--accent-color)', background: 'var(--accent-alpha-08)',
  }}>{text}</span>
);

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">数据源定义</span>
        <Button type="primary" size="small" onClick={() => { setEditing(null); form.resetFields(); setModalOpen(true); }}>新增</Button>
      </div>
      <div className="eakis-page-content">
        <Table size="small" loading={loading} dataSource={items} rowKey="id"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
          columns={[
            { title: '名称', dataIndex: 'name', key: 'name' },
            { title: '平台', dataIndex: 'platform', key: 'platform', width: 110, render: (v: string) => <TokenTag text={v} /> },
            { title: 'API 地址', dataIndex: 'api_base_url', key: 'url', ellipsis: true, render: (v: string) => v || '—' },
            { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true, render: (v: string) => v || '—' },
            { title: '启用', dataIndex: 'is_active', key: 'active', width: 90, render: (v: number) => <DsStatusBadge active={!!v} /> },
            {
              // 行操作统一 type=link size=small（规范 §02 表格页）
              title: '操作', key: 'action', width: 140,
              render: (_, r) => (
                <Space size="small">
                  <Button type="link" size="small" onClick={() => { setEditing(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
                  <Button type="link" size="small" danger onClick={() => handleDelete(r)}>删除</Button>
                </Space>
              ),
            },
          ]}
        />
      </div>
      <Modal title={editing ? `编辑: ${editing.name}` : '新增数据源'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={520}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
            <Select options={[{ value: 'fofa', label: 'Fofa' }, { value: 'shodan', label: 'Shodan' }, { value: 'hunter', label: 'Hunter' }, { value: 'quake', label: 'Quake' }, { value: 'zoomeye', label: 'ZoomEye' }]} />
          </Form.Item>
          <Form.Item name="api_base_url" label="API 地址"><Input placeholder="https://api.xxx.com" /></Form.Item>
          {/* 配置 JSON 编辑：mono 12px/1.5（规范 §05/§06 代码型内容） */}
          <Form.Item name="config" label="配置 (JSON)"><Input.TextArea rows={4} placeholder='{"fields":[],"page_size":100}' style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.5 }} /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DatasourcePage;
