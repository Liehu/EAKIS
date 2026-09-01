import { useEffect } from 'react';
import { Row, Col, Table, Button, Space, Empty } from 'antd';
import { getTask } from '@/api/tasks';
import MetricCard from '@/components/MetricCard';
import AgentPipeline from '@/components/AgentPipeline';
import AgentLog from '@/components/AgentLog';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import { useTaskEvents } from '@/hooks/useTaskEvents';

/**
 * 总览看板（规范 §02 页面骨架 / §05 间距刻度）：
 * - 页面根节点 flex column + height 100% 撑满 AppLayout 主面板，页面级不再自带背景色（外壳统一）
 * - 页头 .eakis-page-header + 内容区 .eakis-page-content
 * - KPI 区走 MetricCard（.eakis-kpi-card：标签 12px / 数值 22px/700）
 * - 内容块统一 .eakis-panel 卡片承载；区块标题 14px/600 var(--text-primary)
 */
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <div className="eakis-page-header-title">总览</div>
      </div>
      <div className="eakis-page-content">
        <Row gutter={12} style={{ marginBottom: 20 }}>
          <Col span={6}><MetricCard title="发现资产数" value={stats.assets_found} delta="较传统方法 +70%" deltaType="up" /></Col>
          <Col span={6}><MetricCard title="接口爬取数" value={stats.interfaces_crawled} delta="漏爬率降至 8%" deltaType="up" /></Col>
          <Col span={6}><MetricCard title="检出漏洞" value={stats.vulns_detected} delta={`高危 12 / 中危 21`} deltaType="down" /></Col>
          {/* 探测进度：数值与百分号分离（value 数值 + suffix 单位），修正原「42%%」重复百分号显示 */}
          <Col span={6}><MetricCard title="探测进度" value={Math.round(currentTask.progress * 100)} suffix="%" delta="预计剩余 4.2 小时" /></Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 20 }}>
          <Col span={12}>
            <div className="eakis-panel" style={{ padding: 16 }}>
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>五层流程 Agent 状态</span>
              </div>
              <AgentPipeline stageDetails={stage_details} />
            </div>
          </Col>
          <Col span={12}>
            <div className="eakis-panel" style={{ padding: 16 }}>
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>高风险资产清单（部分）</span>
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
            </div>
          </Col>
        </Row>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Agent 实时日志</span>
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
    </div>
  );
};

export default Dashboard;
