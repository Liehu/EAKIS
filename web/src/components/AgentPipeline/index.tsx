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

const stageConfig: Record<StageName, { icon: React.ReactNode; label: string }> = {
  intelligence: { icon: <SearchOutlined />, label: '情报收集' },
  keyword_gen: { icon: <TagOutlined />, label: '关键词生成' },
  asset_discovery: { icon: <CloudServerOutlined />, label: '资产关联' },
  api_crawl: { icon: <ApiOutlined />, label: '接口爬取' },
  pentest: { icon: <ThunderboltOutlined />, label: '自动渗透' },
  report_gen: { icon: <ThunderboltOutlined />, label: '报告生成' },
};

const stageColors: Record<string, string> = {
  intelligence: '#378ADD',
  keyword_gen: '#378ADD',
  asset_discovery: '#639922',
  api_crawl: '#BA7517',
  pentest: '#534AB7',
  report_gen: '#534AB7',
};

interface AgentPipelineProps {
  stageDetails: Record<StageName, StageDetail>;
}

const AgentPipeline: React.FC<AgentPipelineProps> = ({ stageDetails }) => {
  const items = (Object.keys(stageConfig) as StageName[]).map((stage) => {
    const detail = stageDetails[stage];
    const config = stageConfig[stage];
    const isDone = detail.status === 'completed';
    const isRunning = detail.status === 'running';
    const progress = detail.progress ?? (isDone ? 1 : 0);

    return {
      key: stage,
      icon: (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 32,
          height: 32,
          borderRadius: 6,
          background: isDone || isRunning ? `${stageColors[stage]}22` : '#2a2a4e',
          color: isDone || isRunning ? stageColors[stage] : '#666',
        }}>
          {config.icon}
        </span>
      ),
      title: (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: isDone || isRunning ? '#e0e0e0' : '#666' }}>
            {config.label}
          </span>
          <StatusBadge status={detail.status} />
        </div>
      ),
      description: (
        <div style={{ opacity: isDone || isRunning ? 1 : 0.5 }}>
          {isDone && detail.keywords && <span style={{ fontSize: 11, color: '#888' }}>已生成 {detail.keywords} 个关键词</span>}
          {isDone && detail.assets && <span style={{ fontSize: 11, color: '#888' }}>发现 {detail.assets} 个资产 · 确认 {detail.confirmed}</span>}
          {isRunning && <span style={{ fontSize: 11, color: '#888' }}>已采集 {detail.interfaces} 个接口</span>}
          {!isDone && !isRunning && <span style={{ fontSize: 11, color: '#666' }}>等待</span>}
          {(isRunning || isDone) && (
            <Progress
              percent={Math.round(progress * 100)}
              showInfo={false}
              strokeColor={stageColors[stage]}
              size="small"
              style={{ marginTop: 4 }}
            />
          )}
        </div>
      ),
    };
  });

  return <Steps direction="vertical" size="small" current={-1} style={{ marginTop: 8 }} items={items} />;
};

export default AgentPipeline;
