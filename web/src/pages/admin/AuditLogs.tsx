import { useEffect, useState } from 'react';
import { Table, Tag, Select, Space, Input, Drawer, Descriptions } from 'antd';
import { getAuditLogs } from '@/api/auditLogs';
import type { AuditLog } from '@/types/auditLog';

const statusCodeColor = (code?: number) => {
  if (!code) return 'default';
  if (code < 300) return 'green';
  if (code < 400) return 'blue';
  if (code < 500) return 'orange';
  return 'red';
};

const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [resourceFilter, setResourceFilter] = useState<string | undefined>();
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<AuditLog | null>(null);

  const fetchLogs = async (p = page) => {
    setLoading(true);
    try {
      const res = await getAuditLogs({
        page: p,
        page_size: 20,
        action: actionFilter,
        resource_type: resourceFilter,
      });
      setLogs(res.data);
      setTotal(res.pagination.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, actionFilter, resourceFilter]);

  const filtered = logs.filter(
    (l) =>
      !search ||
      (l.username || '').includes(search) ||
      (l.request_path || '').includes(search) ||
      (l.ip_address || '').includes(search),
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>审计日志</span>
        <Space>
          <Select
            placeholder="操作类型"
            allowClear
            size="small"
            style={{ width: 140 }}
            value={actionFilter}
            onChange={setActionFilter}
            options={[
              { value: 'LOGIN', label: 'LOGIN' },
              { value: 'LOGOUT', label: 'LOGOUT' },
              { value: 'TASK_CREATE', label: 'TASK_CREATE' },
              { value: 'TASK_UPDATE', label: 'TASK_UPDATE' },
              { value: 'USER_CREATE', label: 'USER_CREATE' },
              { value: 'USER_UPDATE', label: 'USER_UPDATE' },
              { value: 'USER_DELETE', label: 'USER_DELETE' },
              { value: 'CONFIG_UPDATE', label: 'CONFIG_UPDATE' },
            ]}
          />
          <Select
            placeholder="资源类型"
            allowClear
            size="small"
            style={{ width: 120 }}
            value={resourceFilter}
            onChange={setResourceFilter}
            options={[
              { value: 'auth', label: 'auth' },
              { value: 'task', label: 'task' },
              { value: 'user', label: 'user' },
              { value: 'team', label: 'team' },
              { value: 'config', label: 'config' },
              { value: 'asset', label: 'asset' },
              { value: 'vulnerability', label: 'vulnerability' },
            ]}
          />
          <Input.Search placeholder="搜索用户/路径/IP" allowClear size="small" style={{ width: 200 }} onSearch={setSearch} />
        </Space>
      </div>
      <Table
        size="small"
        loading={loading}
        dataSource={filtered}
        rowKey="id"
        onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
        pagination={{
          current: page,
          pageSize: 20,
          total,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        columns={[
          {
            title: '时间', dataIndex: 'created_at', key: 'time', width: 180,
            render: (v: string) => new Date(v).toLocaleString('zh-CN'),
          },
          { title: '用户', dataIndex: 'username', key: 'user', width: 180, render: (v: string) => v || '—' },
          { title: '操作', dataIndex: 'action', key: 'action', width: 140, render: (v: string) => <Tag color="blue">{v}</Tag> },
          { title: '资源', dataIndex: 'resource_type', key: 'resource', width: 120 },
          {
            title: '请求', key: 'request',
            render: (_, r) => (
              <span>
                <Tag>{r.request_method}</Tag>
                <span style={{ color: '#94a3b8', fontSize: 12 }}>{r.request_path}</span>
              </span>
            ),
          },
          {
            title: '状态码', dataIndex: 'status_code', key: 'status', width: 80,
            render: (v?: number) => (v ? <Tag color={statusCodeColor(v)}>{v}</Tag> : '—'),
          },
          { title: '耗时', dataIndex: 'duration_ms', key: 'duration', width: 80, render: (v?: number) => (v ? `${v}ms` : '—') },
          { title: 'IP', dataIndex: 'ip_address', key: 'ip', width: 120, render: (v: string) => v || '—' },
        ]}
      />

      <Drawer
        title="日志详情"
        open={!!selected}
        onClose={() => setSelected(null)}
        width={480}
      >
        {selected && (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="ID">{selected.id}</Descriptions.Item>
              <Descriptions.Item label="时间">{new Date(selected.created_at).toLocaleString('zh-CN')}</Descriptions.Item>
              <Descriptions.Item label="用户">{selected.username || '—'}</Descriptions.Item>
              <Descriptions.Item label="操作">{selected.action}</Descriptions.Item>
              <Descriptions.Item label="资源类型">{selected.resource_type}</Descriptions.Item>
              <Descriptions.Item label="资源 ID">{selected.resource_id || '—'}</Descriptions.Item>
              <Descriptions.Item label="IP">{selected.ip_address || '—'}</Descriptions.Item>
              <Descriptions.Item label="User-Agent">{selected.user_agent || '—'}</Descriptions.Item>
              <Descriptions.Item label="请求方法">{selected.request_method || '—'}</Descriptions.Item>
              <Descriptions.Item label="请求路径">{selected.request_path || '—'}</Descriptions.Item>
              <Descriptions.Item label="状态码">{selected.status_code ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="耗时">{selected.duration_ms ? `${selected.duration_ms}ms` : '—'}</Descriptions.Item>
            </Descriptions>
            {selected.detail && Object.keys(selected.detail).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>详情</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto' }}>
                  {JSON.stringify(selected.detail, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default AuditLogs;
