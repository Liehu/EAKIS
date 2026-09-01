import { Steps, Progress } from 'antd';
import {
  SearchOutlined,
  TagOutlined,
  CloudServerOutlined,
  ApiOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import StatusBadge from '@/components/StatusBadge';
import type { StageName, StageDetail } from '@/types/task';
import './index.css';

const stageConfig: Record<StageName, { icon: React.ReactNode; label: string }> = {
  intelligence: { icon: <SearchOutlined />, label: '情报收集' },
  keyword_gen: { icon: <TagOutlined />, label: '关键词生成' },
  asset_discovery: { icon: <CloudServerOutlined />, label: '资产关联' },
  api_crawl: { icon: <ApiOutlined />, label: '接口爬取' },
  pentest: { icon: <ThunderboltOutlined />, label: '自动渗透' },
  report_gen: { icon: <ThunderboltOutlined />, label: '报告生成' },
};

interface AgentPipelineProps {
  stageDetails: Record<StageName, StageDetail>;
}

/**
 * 智能体流水线（规范 §06）：节点统一令牌化——未激活 --bg-tertiary 底 + --border-color 描边，
 * 激活（完成/运行中）--accent-color + --accent-alpha-08 底；进度条 --accent-color；
 * meta 统计走 --font-mono；连线由 .eakis-pipeline 重涂 --border-color。
 */
const AgentPipeline: React.FC<AgentPipelineProps> = ({ stageDetails }) => {
  const items = (Object.keys(stageConfig) as StageName[]).map((stage) => {
    // 防御性兜底: stageDetails 可能缺少某些阶段 (后端未返回时), 用 pending 占位避免崩溃
    const detail = stageDetails?.[stage] ?? { status: 'pending' as const };
    const config = stageConfig[stage];
    const isDone = detail.status === 'completed';
    const isRunning = detail.status === 'running';
    const isActive = isDone || isRunning;
    const progress = detail.progress ?? (isDone ? 1 : 0);

    return {
      key: stage,
      icon: (
        <span className={`eakis-pipeline-node${isActive ? ' is-active' : ''}`}>
          {config.icon}
        </span>
      ),
      title: (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`eakis-pipeline-title${isActive ? ' is-active' : ''}`}>
            {config.label}
          </span>
          <StatusBadge status={detail.status} />
        </div>
      ),
      description: (
        <div style={{ opacity: isActive ? 1 : 0.5 }}>
          {isDone && detail.keywords && <span className="eakis-pipeline-meta">已生成 {detail.keywords} 个关键词</span>}
          {isDone && detail.assets && <span className="eakis-pipeline-meta">发现 {detail.assets} 个资产 · 确认 {detail.confirmed}</span>}
          {isRunning && <span className="eakis-pipeline-meta">已采集 {detail.interfaces} 个接口</span>}
          {!isDone && !isRunning && <span className="eakis-pipeline-meta">等待</span>}
          {(isRunning || isDone) && (
            <Progress
              percent={Math.round(progress * 100)}
              showInfo={false}
              strokeColor="var(--accent-color)"
              size="small"
              style={{ marginTop: 4 }}
            />
          )}
        </div>
      ),
    };
  });

  return <Steps direction="vertical" size="small" current={-1} className="eakis-pipeline" style={{ marginTop: 8 }} items={items} />;
};

export default AgentPipeline;
