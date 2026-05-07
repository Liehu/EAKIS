import { useEffect, useState } from 'react';
import { Card, Table, Tag, Select, Drawer, Descriptions, Input } from 'antd';
import { getInterfaces } from '@/api/interfaces';
import type { ApiInterface, ApiType, HttpMethod } from '@/types/interface';

const methodColors: Record<HttpMethod, string> = {
  GET: 'green', POST: 'blue', PUT: 'orange', PATCH: 'gold', DELETE: 'red',
};

const Interfaces: React.FC = () => {
  const [interfaces, setInterfaces] = useState<ApiInterface[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<ApiType | undefined>();
  const [selected, setSelected] = useState<ApiInterface | null>(null);

  const fetchInterfaces = async () => {
    setLoading(true);
    try {
      const res = await getInterfaces('task_01J9XXXXX', { type: typeFilter });
      setInterfaces(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchInterfaces(); }, [typeFilter]);

  return (
    <div>
      <Card title="接口列表" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Select placeholder="接口类型" allowClear size="small" style={{ width: 120 }} value={typeFilter} onChange={setTypeFilter}
            options={['query', 'operation', 'upload', 'search', 'auth', 'admin', 'other'].map((t) => ({ value: t, label: t }))} />
        }>
        <Table size="small" loading={loading} dataSource={interfaces} rowKey="id" pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '方法', dataIndex: 'method', key: 'method', width: 80, render: (v: HttpMethod) => <Tag color={methodColors[v]}>{v}</Tag> },
            { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true },
            { title: '类型', dataIndex: 'api_type', key: 'api_type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '优先级', dataIndex: 'test_priority', key: 'priority', width: 70, sorter: (a, b) => a.test_priority - b.test_priority },
            { title: '权限敏感', dataIndex: 'privilege_sensitive', key: 'sensitive', width: 80, render: (v: boolean) => v ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
            { title: '已测试', dataIndex: 'vuln_tested', key: 'tested', width: 70, render: (v: boolean) => v ? '是' : '否' },
            { title: '漏洞', dataIndex: 'vuln_count', key: 'vulns', width: 60 },
          ]}
        />
      </Card>
      <Drawer title={selected?.path} open={!!selected} onClose={() => setSelected(null)} width={600}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="方法"><Tag color={methodColors[selected.method]}>{selected.method}</Tag></Descriptions.Item>
            <Descriptions.Item label="路径"><Input.TextArea value={selected.path} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="类型">{selected.api_type}</Descriptions.Item>
            <Descriptions.Item label="认证要求">{selected.auth_required ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="权限敏感">{selected.privilege_sensitive ? <Tag color="red">是</Tag> : '否'}</Descriptions.Item>
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
                    { title: '敏感', dataIndex: 'sensitive', render: (v: boolean) => v ? <Tag color="red">是</Tag> : '否' },
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
