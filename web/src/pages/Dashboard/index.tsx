import { useEffect, useState } from 'react';
import { Row, Col, Card, Table, Button, Space } from 'antd';
import { getTask } from '@/api/tasks';
import MetricCard from '@/components/MetricCard';
import AgentPipeline from '@/components/AgentPipeline';
import AgentLog from '@/components/AgentLog';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import type { TaskEvent } from '@/types/task';

const mockLogs: TaskEvent[] = [
  { event_type: 'agent_log', timestamp: '2024-01-01T14:32:01Z', data: { message: '关键词生成完成 · 业务词46个 / 技术词29个 / 关联主体词38个' } },
  { event_type: 'agent_log', timestamp: '2024-01-01T14:38:17Z', data: { message: 'Fofa检索完成 · 返回资产2,104条 · 筛选后247条 (误判率11.2%)' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T14:52:44Z', data: { message: '接口爬取Agent启动 · 目标: admin.target.cn · 登录页识别成功', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T14:53:09Z', data: { message: '模拟登录操作 · 捕获POST /api/v2/auth/login · 参数: username/password/captcha', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'vuln_found', timestamp: '2024-01-01T15:01:33Z', data: { message: '反爬检测触发 · 已切换IP代理 · 随机延迟注入 · 继续爬取' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T15:04:22Z', data: { message: '动态接口捕获 · GET /api/user/{id}/detail · 疑似越权参数', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'agent_log', timestamp: '2024-01-01T15:11:58Z', data: { message: '接口特征库更新 · 已训练接口分类模型 · 操作类接口347个 / 查询类891个' } },
];

const Dashboard: React.FC = () => {
  const { currentTask, setCurrentTask } = useTaskStore();
  const [logs] = useState<TaskEvent[]>(mockLogs);

  useEffect(() => {
    if (!currentTask) {
      getTask('task_01J9XXXXX').then(setCurrentTask).catch(console.error);
    }
  }, [currentTask, setCurrentTask]);

  if (!currentTask) return null;

  const { stats, stage_details } = currentTask;

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 20 }}>
        <Col span={6}><MetricCard title="发现资产数" value={stats.assets_found} delta="较传统方法 +70%" deltaType="up" /></Col>
        <Col span={6}><MetricCard title="接口爬取数" value={stats.interfaces_crawled} delta="漏爬率降至 8%" deltaType="up" /></Col>
        <Col span={6}><MetricCard title="检出漏洞" value={stats.vulns_detected} delta={`高危 12 / 中危 21`} deltaType="down" /></Col>
        <Col span={6}><MetricCard title="探测进度" value={`${Math.round(currentTask.progress * 100)}%`} suffix="%" delta="预计剩余 4.2 小时" /></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col span={12}>
          <Card title="五层流程 Agent 状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <AgentPipeline stageDetails={stage_details} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="高风险资产清单（部分）" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <Table
              size="small"
              pagination={false}
              dataSource={[
                { key: '1', asset: 'api.target.com', type: 'API网关', vuln: '未授权访问', risk: 'high' as const },
                { key: '2', asset: 'admin.target.cn', type: '管理后台', vuln: '越权操作', risk: 'high' as const },
                { key: '3', asset: 'search.target.com', type: '搜索接口', vuln: 'SQL注入', risk: 'high' as const },
                { key: '4', asset: 'upload.target.com', type: '文件服务', vuln: '恶意上传', risk: 'medium' as const },
                { key: '5', asset: 'h5.target.com', type: '移动端', vuln: 'XSS', risk: 'medium' as const },
                { key: '6', asset: 'static.target.com', type: '静态资源', vuln: '目录遍历', risk: 'low' as const },
              ]}
              columns={[
                { title: '资产', dataIndex: 'asset', key: 'asset' },
                { title: '类型', dataIndex: 'type', key: 'type' },
                { title: '漏洞', dataIndex: 'vuln', key: 'vuln' },
                { title: '风险', dataIndex: 'risk', key: 'risk', render: (risk: 'high' | 'medium' | 'low') => <RiskTag level={risk} /> },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Agent 实时日志"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Button size="small">暂停</Button>
            <Button size="small">导出报告</Button>
          </Space>
        }
      >
        <AgentLog events={logs} maxHeight={200} />
      </Card>
    </div>
  );
};

export default Dashboard;
