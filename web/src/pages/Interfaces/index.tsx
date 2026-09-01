import { useEffect, useState } from 'react';
import { Table, Select, Drawer, Descriptions, Input } from 'antd';
import { getInterfaces } from '@/api/interfaces';
import { useTaskStore } from '@/store/taskStore';
import type { ApiInterface, ApiType, HttpMethod } from '@/types/interface';

// HTTP 方法语义令牌（契约：GET=success · POST=accent · PUT=warning · DELETE=error，10% 同色底 + 同色字；
// PATCH 契约未点名，按与 PUT 同为更新语态归 warning 族）
const methodTokens: Record<HttpMethod, string> = {
  GET: 'var(--success)', POST: 'var(--accent-color)', PUT: 'var(--warning)', PATCH: 'var(--warning)', DELETE: 'var(--error)',
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

const Interfaces: React.FC = () => {
  const [interfaces, setInterfaces] = useState<ApiInterface[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<ApiType | undefined>();
  const [selected, setSelected] = useState<ApiInterface | null>(null);

  const currentTask = useTaskStore((s) => s.currentTask);
  const taskId = currentTask?.task_id;

  const fetchInterfaces = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const res = await getInterfaces(taskId, { type: typeFilter });
      setInterfaces(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchInterfaces(); }, [typeFilter, taskId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* 页头（规范 §02）：标题 + 类型筛选 */}
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">接口列表</span>
        <Select placeholder="接口类型" allowClear size="small" style={{ width: 120 }} value={typeFilter} onChange={setTypeFilter}
          options={['query', 'operation', 'upload', 'search', 'auth', 'admin', 'other'].map((t) => ({ value: t, label: t }))} />
      </div>
      <div className="eakis-page-content">
        <Table size="small" loading={loading} dataSource={interfaces} rowKey="id" pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '方法', dataIndex: 'method', key: 'method', width: 90, render: (v: HttpMethod) => <TokenBadge color={methodTokens[v]}>{v}</TokenBadge> },
            { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true, render: (v: string) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{v}</span> },
            { title: '类型', dataIndex: 'api_type', key: 'api_type', render: (v: string) => <TokenBadge color="var(--text-secondary)">{v}</TokenBadge> },
            { title: '优先级', dataIndex: 'test_priority', key: 'priority', width: 70, sorter: (a, b) => a.test_priority - b.test_priority },
            { title: '权限敏感', dataIndex: 'privilege_sensitive', key: 'sensitive', width: 90, render: (v: boolean) => v ? <TokenBadge color="var(--error)">是</TokenBadge> : <TokenBadge color="var(--text-muted)">否</TokenBadge> },
            { title: '已测试', dataIndex: 'vuln_tested', key: 'tested', width: 70, render: (v: boolean) => v ? '是' : '否' },
            { title: '漏洞', dataIndex: 'vuln_count', key: 'vulns', width: 60 },
          ]}
        />
      </div>
      <Drawer title={selected?.path} open={!!selected} onClose={() => setSelected(null)} width={600}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="方法"><TokenBadge color={methodTokens[selected.method]}>{selected.method}</TokenBadge></Descriptions.Item>
            <Descriptions.Item label="路径"><Input.TextArea value={selected.path} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="类型">{selected.api_type}</Descriptions.Item>
            <Descriptions.Item label="认证要求">{selected.auth_required ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="权限敏感">{selected.privilege_sensitive ? <TokenBadge color="var(--error)">是</TokenBadge> : '否'}</Descriptions.Item>
            <Descriptions.Item label="敏感参数">{selected.sensitive_params.join(', ') || '无'}</Descriptions.Item>
            <Descriptions.Item label="触发场景">{selected.trigger_scenario}</Descriptions.Item>
            <Descriptions.Item label="测试优先级">{selected.test_priority} / 10</Descriptions.Item>
            <Descriptions.Item label="爬取方式">{selected.crawl_method}</Descriptions.Item>
            <Descriptions.Item label="参数列表">
              {selected.parameters.length > 0 ? (
                <Table size="small" pagination={false} dataSource={selected.parameters} rowKey="name"
                  columns={[
                    { title: '名称', dataIndex: 'name' },
                    { title: '位置', dataIndex: 'location' },
                    { title: '类型', dataIndex: 'type' },
                    { title: '必填', dataIndex: 'required', render: (v: boolean) => v ? '是' : '否' },
                    { title: '敏感', dataIndex: 'sensitive', render: (v: boolean) => v ? <TokenBadge color="var(--error)">是</TokenBadge> : '否' },
                  ]}
                />
              ) : '无参数'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Interfaces;
