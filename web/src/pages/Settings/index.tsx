import { useEffect, useState } from 'react';
import { Tabs, Card, Descriptions, Table, Tag, Switch, Button, Modal, Form, Input, Select, Space, message, Popconfirm, Statistic, Row, Col } from 'antd';
import { PlusOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons';
import { getHealth, getMetrics, getAgentConfigs, updateAgentConfig } from '@/api/system';
import { getProviders, createProvider, deleteProvider, getModelAllocations, getProviderUsage } from '@/api/providers';
import { getWebhooks, createWebhook, deleteWebhook, testWebhook } from '@/api/webhooks';
import type { HealthResponse, MetricsResponse, AgentConfig } from '@/api/system';
import type { AIProvider, ModelAllocation, ProviderUsage } from '@/types/provider';
import type { WebhookConfig, WebhookEventType } from '@/types/webhook';

/* ---------- Agent Config sub-table ---------- */

function AgentConfigTable() {
  const [agents, setAgents] = useState<Record<string, AgentConfig>>({});

  useEffect(() => { getAgentConfigs().then(setAgents); }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    await updateAgentConfig(name, { enabled });
    getAgentConfigs().then(setAgents);
  };

  return (
    <Table size="small" dataSource={Object.entries(agents).map(([name, config]) => ({ key: name, name, ...config }))} pagination={false}
      columns={[
        { title: 'Agent', dataIndex: 'name', key: 'name' },
        { title: '模型', dataIndex: 'model', key: 'model' },
        { title: 'Temperature', dataIndex: 'temperature', key: 'temp', width: 100 },
        { title: 'Max Tokens', dataIndex: 'max_tokens', key: 'tokens', width: 100 },
        { title: '超时(s)', dataIndex: 'timeout_s', key: 'timeout', width: 80 },
        { title: '重试', dataIndex: 'retry_attempts', key: 'retry', width: 60 },
        { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean, record) => <Switch size="small" checked={v} onChange={(val) => handleToggle(record.name, val)} /> },
      ]}
    />
  );
}

/* ---------- Main Settings ---------- */

const Settings: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [allocations, setAllocations] = useState<ModelAllocation[]>([]);
  const [providerUsage, setProviderUsage] = useState<ProviderUsage[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
  const [providerForm] = Form.useForm();
  const [webhookForm] = Form.useForm();
  const [providerModalOpen, setProviderModalOpen] = useState(false);
  const [webhookModalOpen, setWebhookModalOpen] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth);
    getMetrics().then(setMetrics);
    getProviders().then(setProviders);
    getModelAllocations().then(setAllocations);
    getProviderUsage().then(setProviderUsage);
    getWebhooks().then(setWebhooks);
  }, []);

  /* handlers */

  const handleCreateProvider = async (values: { name: string; type: string; api_key: string; base_url: string }) => {
    await createProvider({ ...values, type: values.type as AIProvider['type'] });
    message.success('Provider 添加成功');
    setProviderModalOpen(false);
    providerForm.resetFields();
    getProviders().then(setProviders);
  };

  const handleCreateWebhook = async (values: { url: string; events: WebhookEventType[]; secret: string }) => {
    await createWebhook(values);
    message.success('Webhook 添加成功');
    setWebhookModalOpen(false);
    webhookForm.resetFields();
    getWebhooks().then(setWebhooks);
  };

  const handleTestWebhook = async (id: string) => {
    const res = await testWebhook(id);
    message.success(res.success ? `测试成功 (${res.response_time_ms}ms)` : '测试失败');
  };

  /* tab content */

  const healthTab = (
    <Row gutter={16}>
      <Col span={12}>
        <Card title="健康状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
          {health ? (
            <Descriptions column={2} size="small">
              {Object.entries(health.components).map(([key, val]) => (
                <Descriptions.Item key={key} label={key}>
                  <Tag color={val.status === 'healthy' ? 'green' : 'red'}>{val.status}</Tag>
                  {val.latency_ms != null && <span style={{ color: '#888', fontSize: 11 }}>{val.latency_ms}ms</span>}
                </Descriptions.Item>
              ))}
            </Descriptions>
          ) : '加载中...'}
        </Card>
      </Col>
      <Col span={12}>
        <Card title="系统指标" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
          {metrics ? (
            <Descriptions column={2} size="small">
              <Descriptions.Item label="活跃任务">{metrics.active_tasks}</Descriptions.Item>
              <Descriptions.Item label="队列任务">{metrics.queued_tasks}</Descriptions.Item>
              <Descriptions.Item label="今日完成">{metrics.completed_tasks_today}</Descriptions.Item>
              <Descriptions.Item label="LLM 费用">${metrics.llm_cost_usd_today}</Descriptions.Item>
            </Descriptions>
          ) : '加载中...'}
        </Card>
      </Col>
    </Row>
  );

  const providersTab = (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {providerUsage.map((pu) => (
          <Col span={8} key={pu.provider_id}>
            <Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
              <Statistic title={<span style={{ color: '#888' }}>{pu.provider_name}</span>} value={`$${pu.cost_usd.toFixed(2)}`} valueStyle={{ fontSize: 18 }} />
              <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>调用 {pu.total_calls} 次 · {pu.total_tokens.toLocaleString()} tokens</div>
            </Card>
          </Col>
        ))}
      </Row>
      <Card title="Provider 列表" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={<Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setProviderModalOpen(true)}>添加</Button>}>
        <Table size="small" dataSource={providers} rowKey="id" pagination={false}
          columns={[
            { title: '名称', dataIndex: 'name', key: 'name' },
            { title: '类型', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
            { title: 'Base URL', dataIndex: 'base_url', key: 'url', ellipsis: true },
            { title: 'API Key', dataIndex: 'api_key', key: 'key', render: (v: string) => v ? `${v.slice(0, 7)}****` : '-' },
            { title: '模型', key: 'models', render: (_, r) => r.models.join(', ') },
            { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '禁用'}</Tag> },
            { title: '操作', key: 'action', width: 60, render: (_, r) => <Popconfirm title="确认删除?" onConfirm={() => deleteProvider(r.id).then(() => { message.success('已删除'); getProviders().then(setProviders); })}><Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm> },
          ]}
        />
      </Card>
      <Card title="模型分配" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e', marginTop: 16 }}>
        <Table size="small" dataSource={allocations} rowKey="agent_name" pagination={false}
          columns={[
            { title: 'Agent', dataIndex: 'agent_name', key: 'agent' },
            { title: 'Provider', dataIndex: 'provider_name', key: 'provider' },
            { title: '模型', dataIndex: 'model', key: 'model' },
            { title: '操作', key: 'action', width: 80, render: () => <Button size="small" onClick={() => { message.success('模型分配已更新'); }}>编辑</Button> },
          ]}
        />
      </Card>
    </div>
  );

  const searchSitesTab = (
    <div>
      <Card title="搜索引擎配置" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
        <Table size="small" pagination={false} dataSource={[
          { key: 'fofa', name: 'FOFA', api_key: '****xxxx', quota: '10000次/月', used: 3256, enabled: true },
          { key: 'hunter', name: '鹰图 (Hunter)', api_key: '****yyyy', quota: '5000次/月', used: 1890, enabled: true },
          { key: 'shodan', name: 'Shodan', api_key: '****zzzz', quota: '100次/月', used: 45, enabled: false },
        ]}
          columns={[
            { title: '引擎', dataIndex: 'name', key: 'name' },
            { title: 'API Key', dataIndex: 'api_key', key: 'key' },
            { title: '额度', dataIndex: 'quota', key: 'quota' },
            { title: '已使用', dataIndex: 'used', key: 'used' },
            { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean) => <Switch size="small" checked={v} /> },
            { title: '操作', key: 'action', width: 60, render: () => <Button size="small">编辑</Button> },
          ]}
        />
      </Card>
      <Card title="招投标网站" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e', marginTop: 16 }}>
        <Table size="small" pagination={false} dataSource={[
          { key: 'ccgp', name: '中国政府采购网', url: 'http://www.ccgp.gov.cn', enabled: true },
          { key: 'chinabidding', name: '中国招标网', url: 'https://www.chinabidding.cn', enabled: true },
        ]}
          columns={[
            { title: '网站', dataIndex: 'name', key: 'name' },
            { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
            { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean) => <Switch size="small" checked={v} /> },
            { title: '操作', key: 'action', width: 60, render: () => <Button size="small">编辑</Button> },
          ]}
        />
      </Card>
    </div>
  );

  const keywordTemplatesTab = (
    <Card title="关键词模板" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
      extra={<Button size="small" type="primary" icon={<PlusOutlined />}>新建模板</Button>}>
      <Table size="small" pagination={false} dataSource={[
        { key: 'tpl_001', name: '金融科技通用模板', industry: 'fintech', keywords: 86, updated: '2024-01-01' },
        { key: 'tpl_002', name: '电商行业模板', industry: 'ecommerce', keywords: 72, updated: '2024-01-05' },
        { key: 'tpl_003', name: '政务系统模板', industry: 'government', keywords: 95, updated: '2024-01-10' },
      ]}
        columns={[
          { title: '模板名称', dataIndex: 'name', key: 'name' },
          { title: '行业', dataIndex: 'industry', key: 'industry', render: (v: string) => <Tag>{v}</Tag> },
          { title: '关键词数', dataIndex: 'keywords', key: 'keywords' },
          { title: '更新时间', dataIndex: 'updated', key: 'updated' },
          { title: '操作', key: 'action', width: 120, render: () => <Space><Button size="small">编辑</Button><Button size="small">复制</Button></Space> },
        ]}
      />
    </Card>
  );

  const agentsTab = (
    <Card title="Agent 配置" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
      <AgentConfigTable />
    </Card>
  );

  const webhooksTab = (
    <Card title="Webhook 通知" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
      extra={<Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setWebhookModalOpen(true)}>添加</Button>}>
      <Table size="small" dataSource={webhooks} rowKey="id" pagination={false}
        columns={[
          { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
          { title: '事件', dataIndex: 'events', key: 'events', render: (v: string[]) => v.map((e) => <Tag key={e}>{e}</Tag>) },
          { title: '最近状态', dataIndex: 'last_status', key: 'status', width: 80, render: (v: string) => v ? <Tag color={v === 'success' ? 'green' : 'red'}>{v}</Tag> : '-' },
          { title: '失败次数', dataIndex: 'failure_count', key: 'failures', width: 70 },
          { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 60, render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '是' : '否'}</Tag> },
          { title: '操作', key: 'action', width: 100, render: (_, r) => (
            <Space>
              <Button size="small" icon={<SendOutlined />} onClick={() => handleTestWebhook(r.id)}>测试</Button>
              <Popconfirm title="确认删除?" onConfirm={() => deleteWebhook(r.id).then(() => { message.success('已删除'); getWebhooks().then(setWebhooks); })}>
                <Button size="small" type="text" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Space>
          )},
        ]}
      />
    </Card>
  );

  const concurrencyTab = (
    <Card title="并发与速率设置" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="全局最大并发任务数">5</Descriptions.Item>
        <Descriptions.Item label="单任务 Agent 并发数">3</Descriptions.Item>
        <Descriptions.Item label="接口爬取速率 (请求/秒)">10</Descriptions.Item>
        <Descriptions.Item label="IP 代理池大小">20</Descriptions.Item>
        <Descriptions.Item label="自动切换代理阈值">连续失败 3 次</Descriptions.Item>
        <Descriptions.Item label="请求间隔 (ms)">500 - 2000 (随机)</Descriptions.Item>
      </Descriptions>
      <Button type="primary" size="small" style={{ marginTop: 16 }}>编辑配置</Button>
    </Card>
  );

  const tabItems = [
    { key: 'health', label: '系统状态', children: healthTab },
    { key: 'providers', label: 'AI Provider', children: providersTab },
    { key: 'search-sites', label: '搜索网站', children: searchSitesTab },
    { key: 'keyword-templates', label: '关键词模板', children: keywordTemplatesTab },
    { key: 'agents', label: 'Agent 配置', children: agentsTab },
    { key: 'webhooks', label: 'Webhook', children: webhooksTab },
    { key: 'concurrency', label: '并发设置', children: concurrencyTab },
  ];

  return (
    <>
      <Tabs defaultActiveKey="health" items={tabItems} />

      {/* Modals rendered outside Tabs to avoid context issues */}
      <Modal title="添加 AI Provider" open={providerModalOpen} onCancel={() => setProviderModalOpen(false)} onOk={() => providerForm.submit()}>
        <Form form={providerForm} layout="vertical" onFinish={handleCreateProvider}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'openai', label: 'OpenAI' }, { value: 'qwen', label: '通义千问' }, { value: 'zhipu', label: '智谱' }, { value: 'ollama', label: 'Ollama' }, { value: 'custom', label: '自定义' }]} />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="api_key" label="API Key"><Input.Password /></Form.Item>
        </Form>
      </Modal>

      <Modal title="添加 Webhook" open={webhookModalOpen} onCancel={() => setWebhookModalOpen(false)} onOk={() => webhookForm.submit()}>
        <Form form={webhookForm} layout="vertical" onFinish={handleCreateWebhook}>
          <Form.Item name="url" label="URL" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="events" label="事件类型" rules={[{ required: true }]}>
            <Select mode="multiple" options={[
              { value: 'task.complete', label: '任务完成' },
              { value: 'task.failed', label: '任务失败' },
              { value: 'vuln.critical_found', label: '发现严重漏洞' },
              { value: 'vuln.high_found', label: '发现高危漏洞' },
              { value: 'stage.complete', label: '阶段完成' },
              { value: 'stage.failed', label: '阶段失败' },
            ]} />
          </Form.Item>
          <Form.Item name="secret" label="HMAC Secret"><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default Settings;
