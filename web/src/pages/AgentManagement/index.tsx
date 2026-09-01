import { useEffect, useState } from 'react';
import { Table, Switch, Drawer, Form, InputNumber, Input, Button, message, Space } from 'antd';
import { getAgentConfigs, updateAgentConfig } from '@/api/system';
import type { AgentConfig } from '@/api/system';

const agentDescriptions: Record<string, string> = {
  'KEYWORD-GEN': '关键词生成 Agent',
  'ASSET-DISCOVER': '资产发现 Agent',
  'APICRAWL-BROWSER': '接口爬取 Agent（浏览器模式）',
  'PENTEST-AUTO': '自动渗透 Agent',
  'REPORT-GEN': '报告生成 Agent',
};

// Agent 状态徽章（契约：启用=success · 停用=text-muted · 异常=error；当前数据仅 enabled 布尔，error 预留）
const agentStatusMeta: Record<string, { text: string; token: string }> = {
  enabled: { text: '启用', token: 'var(--success)' },
  disabled: { text: '停用', token: 'var(--text-muted)' },
  error: { text: '异常', token: 'var(--error)' },
};

/** 语义令牌徽章：10% 同色底 + 同色字（§06 徽章形态，对齐 ExportRecords/Tools 的 TokenBadge） */
const TokenBadge: React.FC<{ color: string; children?: React.ReactNode }> = ({ color, children }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '4px 12px',
      borderRadius: 'var(--radius-lg)',
      fontSize: 12,
      fontWeight: 500,
      lineHeight: 1.2,
      color,
      background: `color-mix(in srgb, ${color} 10%, transparent)`,
      whiteSpace: 'nowrap',
    }}
  >
    {children}
  </span>
);

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* 页头（规范 §02） */}
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">Agent 管理</span>
      </div>
      <div className="eakis-page-content">
        {/* Agent 配置表：.eakis-panel 卡片承载 + padding 16 */}
        <div className="eakis-panel" style={{ padding: 16 }}>
          <Table size="small" loading={loading}
            dataSource={Object.entries(agents).map(([name, config]) => ({ key: name, name, ...config }))}
            pagination={false}
            columns={[
              { title: 'Agent', dataIndex: 'name', key: 'name', render: (v: string) => <div><strong>{v}</strong><br /><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{agentDescriptions[v] || ''}</span></div> },
              { title: '模型', dataIndex: 'model', key: 'model' },
              { title: 'Temperature', dataIndex: 'temperature', key: 'temp', width: 100 },
              { title: 'Max Tokens', dataIndex: 'max_tokens', key: 'tokens', width: 100 },
              { title: '超时(s)', dataIndex: 'timeout_s', key: 'timeout', width: 80 },
              { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 120, render: (v: boolean, record) => {
                const meta = agentStatusMeta[v ? 'enabled' : 'disabled'];
                return (
                  <Space size={8}>
                    <TokenBadge color={meta.token}>{meta.text}</TokenBadge>
                    <Switch size="small" checked={v} onChange={(val) => handleToggle(record.name, val)} />
                  </Space>
                );
              } },
              { title: '操作', key: 'action', width: 80, render: (_, record) => <Button type="link" size="small" onClick={() => openEdit(record.name, record)}>配置</Button> },
            ]}
          />
        </div>
      </div>

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
