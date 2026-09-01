import { useEffect, useState } from 'react';
import { Row, Col, Spin } from 'antd';
import StatCard from '@/components/StatCard';
import { getHealth } from '@/api/system';

/**
 * 系统状态页（规范 §02 页面骨架 / §06 状态点）：
 * - 页面根节点 flex column + height 100%；页头 .eakis-page-header + 内容区 .eakis-page-content
 * - KPI 走 StatCard（标签 12px / 数值 22px/700）
 * - 状态点统一 .status-dot（healthy 视为运行中，加 .is-pulsing）：
 *   健康=var(--success) / 降级=var(--warning) / 异常=var(--error)，未知=var(--text-muted)
 * - 服务列表以 .eakis-panel 卡片承载；数据获取/轮询逻辑保持不变
 */

// 健康状态 → 语义令牌 + 运行态脉冲（规范 §03 语义色）
const statusTokenMeta: Record<string, { token: string; pulsing: boolean }> = {
  healthy: { token: 'var(--success)', pulsing: true },
  degraded: { token: 'var(--warning)', pulsing: false },
  down: { token: 'var(--error)', pulsing: false },
};
const unknownStatusMeta = { token: 'var(--text-muted)', pulsing: false };

const StatusPage: React.FC = () => {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealth(data as unknown as Record<string, unknown>);
      } catch {
        setHealth({
          status: 'healthy',
          version: 'v2.0.0',
          timestamp: new Date().toISOString(),
          components: {
            database: { status: 'healthy', latency_ms: 2 },
            redis: { status: 'healthy', latency_ms: 1 },
            qdrant: { status: 'healthy', latency_ms: 5 },
            kafka: { status: 'healthy', lag: 0 },
            llm_qwen: { status: 'healthy', latency_ms: 145 },
            playwright: { status: 'healthy', pool_size: 5 },
          },
        });
      } finally {
        setLoading(false);
      }
    };
    fetchHealth();
    const timer = setInterval(fetchHealth, 30000);
    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Spin size="large" />
        </div>
      </div>
    );
  }

  const components = (health?.components || {}) as Record<string, { status: string; latency_ms?: number; lag?: number; pool_size?: number }>;
  const overall = statusTokenMeta[(health?.status as string) || ''] || unknownStatusMeta;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <div className="eakis-page-header-title">系统状态</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            className={`status-dot${overall.pulsing ? ' is-pulsing' : ''}`}
            style={{ background: overall.token }}
          />
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {(health?.status as string) || 'unknown'}
          </span>
        </div>
      </div>
      <div className="eakis-page-content">
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          <Col span={8}>
            <StatCard title="系统状态" value={(health?.status as string) || 'unknown'} color={overall.token} />
          </Col>
          <Col span={8}>
            <StatCard title="版本" value={(health?.version as string) || '-'} />
          </Col>
          <Col span={8}>
            <StatCard title="组件数" value={Object.keys(components).length} />
          </Col>
        </Row>

        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>组件健康状态</div>
        <Row gutter={[16, 16]}>
          {Object.entries(components).map(([name, info]) => {
            const meta = statusTokenMeta[info.status] || unknownStatusMeta;
            return (
              <Col key={name} xs={24} sm={12} lg={8}>
                <div className="eakis-panel" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{name}</span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span
                        className={`status-dot${meta.pulsing ? ' is-pulsing' : ''}`}
                        style={{ background: meta.token }}
                      />
                      <span style={{ fontSize: 12, fontWeight: 500, color: meta.token }}>{info.status}</span>
                    </span>
                  </div>
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    {info.latency_ms != null && <span>{info.latency_ms}ms</span>}
                    {info.lag != null && <span>lag: {info.lag}</span>}
                    {info.pool_size != null && <span>pool: {info.pool_size}</span>}
                  </div>
                </div>
              </Col>
            );
          })}
        </Row>
      </div>
    </div>
  );
};

export default StatusPage;
