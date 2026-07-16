import { useEffect } from 'react';
import { Descriptions, Tag, Empty, Typography } from 'antd';
import GraphPanel from '@/components/GraphPanel';
import { useRightPanelStore, type PanelKind } from '@/store/rightPanelStore';
import { useLocation } from 'react-router-dom';

const { Text } = Typography;

function statusColor(status: string): string {
  const map: Record<string, string> = {
    running: 'processing', completed: 'success', failed: 'error',
    pending: 'default', draft: 'default', published: 'success',
    pending_review: 'processing', deprecated: 'warning',
    confirmed: 'success', false_positive: 'default',
  };
  return map[status] || 'default';
}

/** Markdown / 纯文本预览（带滚动） */
function DocPreview({ content, label }: { content: string | null | undefined; label: string }) {
  if (!content) return <Empty description={`暂无${label}内容`} />;
  return (
    <pre style={{
      background: '#0d0d1a', color: '#cbd5e1', padding: 12, borderRadius: 6,
      fontSize: 12, lineHeight: 1.6, maxHeight: '70vh', overflow: 'auto',
      whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
    }}>
      {content}
    </pre>
  );
}

function TaskDetail({ item }: { item: Record<string, any> }) {
  return (
    <Descriptions column={1} size="small" bordered
      labelStyle={{ background: '#141422', color: '#888', width: 110, whiteSpace: 'nowrap' }}
      contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
      <Descriptions.Item label="任务ID">{item.task_id || '-'}</Descriptions.Item>
      <Descriptions.Item label="企业">{item.company_name || '-'}</Descriptions.Item>
      <Descriptions.Item label="状态">
        {item.status ? <Tag color={statusColor(item.status)}>{item.status}</Tag> : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="当前阶段">{item.current_stage || '-'}</Descriptions.Item>
      <Descriptions.Item label="进度">
        {item.progress != null ? `${Math.round(item.progress * 100)}%` : '-'}
      </Descriptions.Item>
      {item.stats && (
        <Descriptions.Item label="统计">
          资产 {item.stats.assets_found || 0}(确认{item.stats.assets_confirmed || 0}) ·
          接口 {item.stats.interfaces_crawled || 0} ·
          漏洞 {item.stats.vulns_detected || 0}(确认{item.stats.vulns_confirmed || 0})
        </Descriptions.Item>
      )}
      <Descriptions.Item label="创建时间">{item.created_at?.slice(0, 19).replace('T', ' ') || '-'}</Descriptions.Item>
      {item.started_at && (
        <Descriptions.Item label="开始时间">{item.started_at.slice(0, 19).replace('T', ' ')}</Descriptions.Item>
      )}
    </Descriptions>
  );
}

function KnowledgeDetail({ item, subtype }: { item: Record<string, any>; subtype: string | null }) {
  // 各知识库类型的预览内容字段不同
  const previewField: Record<string, string> = {
    vuln: 'poc', payload: 'content', fingerprint: 'match_rule', handbook: 'content',
  };
  const field = (subtype && previewField[subtype]) || 'content';
  return (
    <div>
      <Descriptions column={1} size="small" bordered
        labelStyle={{ background: '#141422', color: '#888', width: 100, whiteSpace: 'nowrap' }}
        contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
        <Descriptions.Item label="名称">{item.name || item.title || '-'}</Descriptions.Item>
        {item.severity && <Descriptions.Item label="严重度"><Tag color={statusColor(item.severity)}>{item.severity}</Tag></Descriptions.Item>}
        {item.category && <Descriptions.Item label="分类">{item.category}</Descriptions.Item>}
        {item.component && <Descriptions.Item label="组件">{item.component}</Descriptions.Item>}
        {item.platform && <Descriptions.Item label="平台">{item.platform}</Descriptions.Item>}
        {item.status && <Descriptions.Item label="状态"><Tag color={statusColor(item.status)}>{item.status}</Tag></Descriptions.Item>}
        {item.summary && <Descriptions.Item label="摘要"><Text type="secondary">{item.summary}</Text></Descriptions.Item>}
        {item.remediation && <Descriptions.Item label="修复建议"><Text>{item.remediation}</Text></Descriptions.Item>}
        {item.tags && Array.isArray(item.tags) && item.tags.length > 0 && (
          <Descriptions.Item label="标签">{item.tags.map((t: string) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>
        )}
      </Descriptions>
      {item[field] && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>{field === 'poc' ? 'POC' : '内容预览'}</Text>
          <div style={{ marginTop: 4 }}>
            <DocPreview content={item[field]} label={field} />
          </div>
        </div>
      )}
    </div>
  );
}

function TemplateDetail({ item }: { item: Record<string, any> }) {
  const content = item.content;
  return (
    <div>
      <Descriptions column={1} size="small" bordered
        labelStyle={{ background: '#141422', color: '#888', width: 100, whiteSpace: 'nowrap' }}
        contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
        <Descriptions.Item label="名称">{item.name || '-'}</Descriptions.Item>
        {item.description && <Descriptions.Item label="描述"><Text type="secondary">{item.description}</Text></Descriptions.Item>}
        {item.scope && <Descriptions.Item label="可见域">{item.scope}</Descriptions.Item>}
        {item.version && <Descriptions.Item label="版本">{item.version}</Descriptions.Item>}
      </Descriptions>
      <div style={{ marginTop: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>模板内容</Text>
        <div style={{ marginTop: 4 }}>
          {content && typeof content === 'object' && (content as any).template ? (
            // prompt 模板：显示 Jinja2 字符串
            <DocPreview content={(content as any).template} label="Prompt" />
          ) : (
            <DocPreview content={content ? JSON.stringify(content, null, 2) : null} label="JSON" />
          )}
        </div>
      </div>
    </div>
  );
}

function ToolDetail({ item, subtype }: { item: Record<string, any>; subtype: string | null }) {
  if (subtype === 'execution') {
    return (
      <div>
        <Descriptions column={1} size="small" bordered
          labelStyle={{ background: '#141422', color: '#888', width: 100, whiteSpace: 'nowrap' }}
          contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
          <Descriptions.Item label="工具">{item.tool_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {item.status ? <Tag color={statusColor(item.status)}>{item.status}</Tag> : '-'}
          </Descriptions.Item>
          {item.exit_code != null && <Descriptions.Item label="退出码">{item.exit_code}</Descriptions.Item>}
          {item.duration_s != null && <Descriptions.Item label="耗时">{item.duration_s}s</Descriptions.Item>}
        </Descriptions>
        {item.stdout && (
          <div style={{ marginTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>输出</Text>
            <div style={{ marginTop: 4 }}><DocPreview content={item.stdout} label="stdout" /></div>
          </div>
        )}
        {item.parsed && (
          <div style={{ marginTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>解析结果</Text>
            <div style={{ marginTop: 4 }}><DocPreview content={JSON.stringify(item.parsed, null, 2)} label="parsed" /></div>
          </div>
        )}
      </div>
    );
  }
  // 工具信息
  return (
    <Descriptions column={1} size="small" bordered
      labelStyle={{ background: '#141422', color: '#888', width: 100, whiteSpace: 'nowrap' }}
      contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
      <Descriptions.Item label="名称">{item.name || '-'}</Descriptions.Item>
      <Descriptions.Item label="二进制">{item.binary || '-'}</Descriptions.Item>
      {item.description && <Descriptions.Item label="描述"><Text type="secondary">{item.description}</Text></Descriptions.Item>}
      {item.category && <Descriptions.Item label="分类">{item.category}</Descriptions.Item>}
      {item.enabled != null && <Descriptions.Item label="状态">{item.enabled ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag>}</Descriptions.Item>}
    </Descriptions>
  );
}

function ReportDetail({ item }: { item: Record<string, any> }) {
  return (
    <div>
      <Descriptions column={1} size="small" bordered
        labelStyle={{ background: '#141422', color: '#888', width: 100, whiteSpace: 'nowrap' }}
        contentStyle={{ background: '#1a1a2e', color: '#e2e8f0' }}>
        <Descriptions.Item label="报告ID">{item.report_id || '-'}</Descriptions.Item>
        <Descriptions.Item label="状态">
          {item.status ? <Tag color={statusColor(item.status)}>{item.status}</Tag> : '-'}
        </Descriptions.Item>
        {item.quality_score && (
          <Descriptions.Item label="质量评分">
            总分 {item.quality_score.overall ?? '-'}
            （准确{item.quality_score.accuracy ?? '-'} · 完整{item.quality_score.completeness ?? '-'} · 可读{item.quality_score.readability ?? '-'}）
          </Descriptions.Item>
        )}
        {item.page_count != null && <Descriptions.Item label="页数">{item.page_count}</Descriptions.Item>}
        {item.word_count != null && <Descriptions.Item label="字数">{item.word_count}</Descriptions.Item>}
        {item.generated_at && <Descriptions.Item label="生成时间">{item.generated_at.slice(0, 19).replace('T', ' ')}</Descriptions.Item>}
      </Descriptions>
      {item.content && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>报告内容预览</Text>
          <div style={{ marginTop: 4 }}><DocPreview content={item.content} label="报告" /></div>
        </div>
      )}
    </div>
  );
}

const PANEL_TITLES: Record<PanelKind, string> = {
  graph: '关系图谱',
  task: '任务详情',
  knowledge: '条目详情',
  template: '模板预览',
  tool: '工具详情',
  report: '报告预览',
};

const RightPanel: React.FC = () => {
  const location = useLocation();
  const { kind, item, subtype, clear } = useRightPanelStore();

  // 路由变化时重置面板
  useEffect(() => {
    clear();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const title = PANEL_TITLES[kind] || '详情';

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#1a1a2e', borderRadius: 28, overflow: 'hidden',
    }}>
      <div style={{
        padding: '16px 20px', fontWeight: 700, borderBottom: '1px solid #2a2a4e',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        color: '#e2e8f0', flexShrink: 0,
      }}>
        <span>{title}</span>
        {subtype && <span style={{ fontSize: 11, color: '#666' }}>{subtype}</span>}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {kind === 'graph' ? (
          <div style={{ height: '100%', margin: -16 }}>
            <GraphPanel />
          </div>
        ) : !item ? (
          <Empty description={`选择条目后在此显示${title}`} style={{ marginTop: 60 }} />
        ) : kind === 'task' ? (
          <TaskDetail item={item} />
        ) : kind === 'knowledge' ? (
          <KnowledgeDetail item={item} subtype={subtype} />
        ) : kind === 'template' ? (
          <TemplateDetail item={item} />
        ) : kind === 'tool' ? (
          <ToolDetail item={item} subtype={subtype} />
        ) : kind === 'report' ? (
          <ReportDetail item={item} />
        ) : (
          <Empty description="暂无数据" />
        )}
      </div>
    </div>
  );
};

export default RightPanel;
