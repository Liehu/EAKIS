import { useEffect } from 'react';
import { Row, Col, Table, Button, Space, Empty } from 'antd';
import { getTask } from '@/api/tasks';
import MetricCard from '@/components/MetricCard';
import AgentPipeline from '@/components/AgentPipeline';
import AgentLog from '@/components/AgentLog';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import { useTaskEvents } from '@/hooks/useTaskEvents';

const Dashboard: React.FC = () => {
  const currentTask = useTaskStore((s) => s.currentTask);
  const setCurrentTask = useTaskStore((s) => s.setCurrentTask);
  const events = useTaskStore((s) => s.events);

  // Subscribe to real-time task events via WebSocket (S0-P1b: replaces hardcoded mockLogs)
  useTaskEvents(currentTask?.task_id);

  useEffect(() => {
    if (!currentTask) return;
    getTask(currentTask.task_id).then(setCurrentTask).catch(console.error);
  }, [currentTask?.task_id]);

  if (!currentTask) return null;

  const stats = (currentTask as any).stats || { assets_found: 0, assets_confirmed: 0, interfaces_crawled: 0, vulns_detected: 0, vulns_confirmed: 0 };
  const stage_details = (currentTask as any).stage_details || {};

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
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>五层流程 Agent 状态</span>
          </div>
          <AgentPipeline stageDetails={stage_details} />
        </Col>
        <Col span={12}>
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>高风险资产清单（部分）</span>
          </div>
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
        </Col>
      </Row>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>Agent 实时日志</span>
        <Space>
          <Button size="small">暂停</Button>
          <Button size="small">导出报告</Button>
        </Space>
      </div>
      {events.length > 0 ? (
        <AgentLog events={events} maxHeight={200} />
      ) : (
        <Empty description="暂无实时日志（等待任务事件推送）" style={{ padding: 32 }} />
      )}
    </div>
  );
};

export default Dashboard;
