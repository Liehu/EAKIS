import { useEffect, useState } from 'react';
import { Card, Table, Tag, Switch, Drawer, Descriptions, Form, InputNumber, Input, Button, message } from 'antd';
import { getAgentConfigs, updateAgentConfig } from '@/api/system';
import type { AgentConfig } from '@/api/system';

const agentDescriptions: Record<string, string> = {
  'KEYWORD-GEN': '关键词生成 Agent',
  'ASSET-DISCOVER': '资产发现 Agent',
  'APICRAWL-BROWSER': '接口爬取 Agent（浏览器模式）',
  'PENTEST-AUTO': '自动渗透 Agent',
  'REPORT-GEN': '报告生成 Agent',
};

const AgentManagement: React.FC = () => {
  const [agents, setAgents] = useState<Record<string, AgentConfig>>({});
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchAgents = async () => {
    setLoading(true);
    try { const res = await getAgentConfigs(); setAgents(res); } finally { setLoading(false); }
  };

  useEffect(() => { fetchAgents(); }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    await updateAgentConfig(name, { enabled });
    message.success(enabled ? '已启用' : '已禁用');
    fetchAgents();
  };

  const openEdit = (name: string, config: AgentConfig) => {
    form.setFieldsValue(config);
    setEditing(name);
  };

  const handleSave = async () => {
    if (!editing) return;
    const values = await form.validateFields();
    await updateAgentConfig(editing, values);
    message.success('配置已保存');
    setEditing(null);
    fetchAgents();
  };

  return (
    <div>
      <Card title="Agent 管理" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
        <Table size="small" loading={loading}
          dataSource={Object.entries(agents).map(([name, config]) => ({ key: name, name, ...config }))}
          pagination={false}
          columns={[
            { title: 'Agent', dataIndex: 'name', key: 'name', render: (v: string) => <div><strong>{v}</strong><br /><span style={{ fontSize: 11, color: '#888' }}>{agentDescriptions[v] || ''}</span></div> },
            { title: '模型', dataIndex: 'model', key: 'model' },
            { title: 'Temperature', dataIndex: 'temperature', key: 'temp', width: 100 },
            { title: 'Max Tokens', dataIndex: 'max_tokens', key: 'tokens', width: 100 },
            { title: '超时(s)', dataIndex: 'timeout_s', key: 'timeout', width: 80 },
            { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean, record) => <Switch size="small" checked={v} onChange={(val) => handleToggle(record.name, val)} /> },
            { title: '操作', key: 'action', width: 80, render: (_, record) => <Button size="small" onClick={() => openEdit(record.name, record)}>配置</Button> },
          ]}
        />
      </Card>

      <Drawer title={`编辑 Agent: ${editing}`} open={!!editing} onClose={() => setEditing(null)} width={400}
        extra={<Button type="primary" size="small" onClick={handleSave}>保存</Button>}>
        <Form form={form} layout="vertical">
          <Form.Item name="model" label="模型"><Input /></Form.Item>
          <Form.Item name="temperature" label="Temperature"><InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="max_tokens" label="Max Tokens"><InputNumber min={256} max={32768} step={256} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="timeout_s" label="超时 (秒)"><InputNumber min={10} max={3600} step={10} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="retry_attempts" label="重试次数"><InputNumber min={0} max={10} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default AgentManagement;
