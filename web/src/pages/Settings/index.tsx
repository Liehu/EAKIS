import { useEffect, useState } from 'react';
import { Card, Descriptions, Table, Tag, Switch, Row, Col, message } from 'antd';
import { getHealth, getMetrics, getAgentConfigs, updateAgentConfig } from '@/api/system';
import type { HealthResponse, MetricsResponse, AgentConfig } from '@/api/system';

const Settings: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [agents, setAgents] = useState<Record<string, AgentConfig>>({});

  useEffect(() => {
    getHealth().then(setHealth).catch(console.error);
    getMetrics().then(setMetrics).catch(console.error);
    getAgentConfigs().then(setAgents).catch(console.error);
  }, []);

  const handleUpdate = async (name: string, field: string, value: unknown) => {
    await updateAgentConfig(name, { [field]: value });
    message.success('配置已更新');
    getAgentConfigs().then(setAgents);
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="系统健康状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
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
                <Descriptions.Item label="平均耗时">{metrics.avg_task_duration_h}h</Descriptions.Item>
                <Descriptions.Item label="LLM 调用">{metrics.llm_calls_today}</Descriptions.Item>
                <Descriptions.Item label="LLM 费用">${metrics.llm_cost_usd_today}</Descriptions.Item>
                <Descriptions.Item label="今日发现资产">{metrics.assets_discovered_today}</Descriptions.Item>
                <Descriptions.Item label="今日确认漏洞">{metrics.vulns_confirmed_today}</Descriptions.Item>
              </Descriptions>
            ) : '加载中...'}
          </Card>
        </Col>
      </Row>
      <Card title="Agent 配置" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
        <Table size="small" dataSource={Object.entries(agents).map(([name, config]) => ({ key: name, name, ...config }))} pagination={false}
          columns={[
            { title: 'Agent', dataIndex: 'name', key: 'name' },
            { title: '模型', dataIndex: 'model', key: 'model' },
            { title: 'Temperature', dataIndex: 'temperature', key: 'temp', width: 100 },
            { title: 'Max Tokens', dataIndex: 'max_tokens', key: 'tokens', width: 100 },
            { title: '超时(s)', dataIndex: 'timeout_s', key: 'timeout', width: 80 },
            { title: '重试', dataIndex: 'retry_attempts', key: 'retry', width: 60 },
            { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean, record) => <Switch size="small" checked={v} onChange={(val) => handleUpdate(record.name, 'enabled', val)} /> },
          ]}
        />
      </Card>
    </div>
  );
};

export default Settings;
