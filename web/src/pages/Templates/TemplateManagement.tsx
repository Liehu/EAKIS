import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space, Tabs, Drawer, InputNumber, Switch, Checkbox } from 'antd';
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '@/api/templates';
import type { Template, TemplateType } from '@/types/template';
import DAGViewer from './DAGViewer';
import { useRightPanelStore } from '@/store/rightPanelStore';

const typeLabel: Record<TemplateType, string> = {
  task: '任务模板', report: '报告模板', prompt: '提示词', attack_path: '攻击路径',
};
const typeColor: Record<TemplateType, string> = {
  task: 'blue', report: 'green', prompt: 'purple', attack_path: 'orange',
};
const scopeLabel: Record<string, string> = { org: '组织', team: '团队', private: '个人' };

// 报告可选字段
const REPORT_FIELDS = ['ip', 'domain', 'port', 'tech_stack', 'risk_level', 'icp_entity', 'open_ports',
  'company_name', 'asset_summary', 'vuln_summary', 'risk_score', 'risk_trend', 'recommendations', 'legal_person', 'credit_code'];

const TemplateManagement: React.FC = () => {
  const location = useLocation();
  const seg = location.pathname.split('/').pop() || 'task';
  const routeType: TemplateType = seg === 'attack' ? 'attack_path' : (['task','report','prompt','attack_path'].includes(seg) ? seg as TemplateType : 'task');
  const [type, setType] = useState<TemplateType>(routeType);
  const [items, setItems] = useState<Template[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Template | null>(null);
  const [form] = Form.useForm();

  const [detail, setDetail] = useState<Template | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const fetchItems = async (p = page) => {
    setLoading(true);
    try {
      const res = await getTemplates({ page: p, page_size: 20, template_type: type, q: q || undefined });
      setItems(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { setPage(1); fetchItems(1); }, [type, q]); // eslint-disable-line
  useEffect(() => { fetchItems(page); }, [page]); // eslint-disable-line

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ template_type: type, scope: 'org' });
    if (type === 'task') form.setFieldsValue({ content: { target_depth: 3, modules: ['M1', 'M3'], concurrency: 5, smart_c_segment: true } });
    if (type === 'report') form.setFieldsValue({ content: { report_type: 'asset', fields: ['ip', 'domain', 'risk_level'], format: 'md', cover: true } });
    if (type === 'prompt') form.setFieldsValue({ content: { agent: '', template: '', variables: [] } });
    if (type === 'attack_path') form.setFieldsValue({ content: { nodes: [], edges: [] } });
    setModalOpen(true);
  };

  const openEdit = (t: Template) => {
    setEditing(t);
    form.setFieldsValue({ name: t.name, description: t.description, scope: t.scope, parent_template_id: t.parent_template_id, content: t.content });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) { await updateTemplate(editing.id, values); message.success('已更新'); }
      else { await createTemplate({ ...values, template_type: type }); message.success('已创建'); }
      setModalOpen(false); fetchItems();
    } catch { message.error('操作失败'); }
  };

  const handleDelete = (t: Template) => {
    Modal.confirm({
      title: `删除模板 "${t.name}"?`, okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => { try { await deleteTemplate(t.id); message.success('已删除'); fetchItems(); } catch { message.error('失败'); } },
    });
  };

  // ── 类型专属 content 编辑器 ──
  const renderContentEditor = () => {
    if (type === 'task') {
      return (
        <>
          <Form.Item name={['content', 'target_depth']} label="穿透深度"><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name={['content', 'modules']} label="启用模块">
            <Checkbox.Group options={[{label:'M1 情报',value:'M1'},{label:'M2 关键词',value:'M2'},{label:'M3 资产',value:'M3'},{label:'M4 接口',value:'M4'}]} />
          </Form.Item>
          <Form.Item name={['content', 'concurrency']} label="并发数"><InputNumber min={1} max={50} /></Form.Item>
          <Form.Item name={['content', 'smart_c_segment']} label="智能C段" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name={['content', 'smart_asset_link']} label="智能资产关联" valuePropName="checked"><Switch /></Form.Item>
        </>
      );
    }
    if (type === 'report') {
      return (
        <>
          <Form.Item name={['content', 'report_type']} label="报告类型" rules={[{ required: true }]}>
            <Select options={[{value:'asset',label:'资产报告'},{value:'company',label:'企业报告'},{value:'vuln',label:'漏洞报告'}]} />
          </Form.Item>
          <Form.Item name={['content', 'fields']} label="输出字段">
            <Checkbox.Group options={REPORT_FIELDS.map((f) => ({ label: f, value: f }))} />
          </Form.Item>
          <Form.Item name={['content', 'format']} label="格式">
            <Select options={[{value:'md',label:'Markdown'},{value:'html',label:'HTML'}]} />
          </Form.Item>
          <Form.Item name={['content', 'cover']} label="封面" valuePropName="checked"><Switch /></Form.Item>
        </>
      );
    }
    if (type === 'prompt') {
      return (
        <>
          <Form.Item name={['content', 'agent']} label="Agent" rules={[{ required: true }]}>
            <Select options={[{value:'M2',label:'M2 关键词'},{value:'M3',label:'M3 资产'},{value:'M4',label:'M4 接口'},{value:'M6',label:'M6 报告'}]} />
          </Form.Item>
          <Form.Item name={['content', 'template']} label="提示词 (Jinja2, 支持 {{var}})" rules={[{ required: true }]}>
            <Input.TextArea rows={6} style={{ fontFamily: 'monospace' }} placeholder="你是一个...请根据 {{input}} ..." />
          </Form.Item>
        </>
      );
    }
    // attack_path: JSON 编辑器
    return (
      <Form.Item name={['content']} label="DAG 内容 (JSON)">
        <Input.TextArea rows={10} style={{ fontFamily: 'monospace' }}
          placeholder='{"nodes":[{"id":"n1","type":"recon","label":"信息收集"}],"edges":[{"source":"n1","target":"n2","action":"auto"}]}' />
      </Form.Item>
    );
  };

  return (
    <div>
      <Tabs
        activeKey={type}
        onChange={(k) => setType(k as TemplateType)}
        items={(Object.keys(typeLabel) as TemplateType[]).map((t) => ({ key: t, label: <Tag color={typeColor[t]}>{typeLabel[t]}</Tag> }))}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>{typeLabel[type]}</span>
        <Space>
          <Input.Search placeholder="搜索名称" allowClear size="small" style={{ width: 180 }} onSearch={setQ} />
          <Button type="primary" size="small" onClick={openCreate}>新增</Button>
        </Space>
      </div>
      <Table size="small" loading={loading} dataSource={items} rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
        onRow={(r) => ({ onClick: () => { setDetail(r); setDrawerOpen(true); setPanelItem('template', r as unknown as Record<string, unknown>, seg); }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true,
            render: (v: string, r: Template) => <span>{v} {r.parent_name && <Tag color="cyan" style={{fontSize:10}}>继承 {r.parent_name}</Tag>}</span> },
          { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true, render: (v: string) => v || '—' },
          { title: '可见域', dataIndex: 'scope', key: 'scope', width: 80, render: (v: string) => <Tag>{scopeLabel[v]}</Tag> },
          { title: '版本', dataIndex: 'version', key: 'ver', width: 60 },
          { title: '种子', dataIndex: 'is_seed', key: 'seed', width: 60, render: (v: number) => v ? <Tag color="gold">种子</Tag> : null },
          {
            title: '操作', key: 'action', width: 140,
            render: (_, r) => (
              <Space size="small" onClick={(e) => e.stopPropagation()}>
                <Button size="small" onClick={() => openEdit(r)}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(r)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal title={editing ? `编辑: ${editing.name}` : `新增${typeLabel[type]}`} open={modalOpen}
        onCancel={() => setModalOpen(false)} onOk={handleSubmit} okText="保存" cancelText="取消" width={640} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Space style={{ display: 'flex' }}>
            <Form.Item name="scope" label="可见域" style={{ width: 150 }}>
              <Select options={[{value:'org',label:'组织'}, {value:'team',label:'团队'}, {value:'private',label:'个人'}]} />
            </Form.Item>
            <Form.Item name="parent_template_id" label="继承父模板" style={{ width: 200 }}>
              <Select allowClear placeholder="无 (顶级)" options={items.filter((i) => i.template_type === type).map((i) => ({ value: i.id, label: i.name }))} />
            </Form.Item>
          </Space>
          <div style={{ marginTop: 8, marginBottom: 8, color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>类型专属内容</div>
          {renderContentEditor()}
        </Form>
      </Modal>

      <Drawer title={detail?.name} open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560}>
        {detail && (
          <>
            <p><strong>类型:</strong> <Tag color={typeColor[detail.template_type]}>{typeLabel[detail.template_type]}</Tag> <strong>可见域:</strong> <Tag>{scopeLabel[detail.scope]}</Tag> <strong>版本:</strong> {detail.version}</p>
            {detail.parent_name && <p><strong>继承自:</strong> <Tag color="cyan">{detail.parent_name}</Tag></p>}
            {detail.description && <p><strong>描述:</strong> {detail.description}</p>}
            {detail.template_type === 'attack_path' ? (
              <div style={{ marginTop: 12 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>攻击路径 DAG</div>
                <DAGViewer nodes={(detail.content as any).nodes || []} edges={(detail.content as any).edges || []} />
                <details style={{ marginTop: 12 }}>
                  <summary style={{ cursor: 'pointer', color: '#94a3b8', fontSize: 12 }}>原始 JSON</summary>
                  <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto' }}>{JSON.stringify(detail.content, null, 2)}</pre>
                </details>
              </div>
            ) : (
              <div style={{ marginTop: 12 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>内容</div>
                {detail.template_type === 'prompt' ? (
                  <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{(detail.content as any).template}</pre>
                ) : (
                  <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto' }}>{JSON.stringify(detail.content, null, 2)}</pre>
                )}
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default TemplateManagement;
