import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, Drawer, Descriptions, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { getCompanies, createCompany, deleteCompany } from '@/api/companies';
import type { Company } from '@/types/company';

const industryLabels: Record<string, string> = { fintech: '金融科技', ecommerce: '电商', tech: '互联网', government: '政务', healthcare: '医疗' };

const Companies: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<Company | null>(null);
  const [form] = Form.useForm();

  const fetchCompanies = async () => {
    setLoading(true);
    try { const res = await getCompanies(); setCompanies(res.data); } finally { setLoading(false); }
  };

  useEffect(() => { fetchCompanies(); }, []);

  const handleCreate = async (values: { name: string; industry: string; domains: string; ip_ranges: string; aliases: string }) => {
    await createCompany({
      ...values,
      domains: values.domains?.split(',').map((s) => s.trim()).filter(Boolean) || [],
      ip_ranges: values.ip_ranges?.split(',').map((s) => s.trim()).filter(Boolean) || [],
      aliases: values.aliases?.split(',').map((s) => s.trim()).filter(Boolean) || [],
    });
    message.success('企业添加成功');
    setCreateOpen(false);
    form.resetFields();
    fetchCompanies();
  };

  const handleDelete = async (id: string) => {
    await deleteCompany(id);
    message.success('已删除');
    fetchCompanies();
  };

  return (
    <div>
      <Card title="企业靶标管理" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={<Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>添加企业</Button>}>
        <Table size="small" loading={loading} dataSource={companies} rowKey="id" pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '企业名称', dataIndex: 'name', key: 'name' },
            { title: '行业', dataIndex: 'industry', key: 'industry', render: (v: string) => <Tag>{industryLabels[v] || v}</Tag> },
            { title: '关联域名', key: 'domains', render: (_, r) => r.domains.join(', ') },
            { title: '任务数', dataIndex: 'task_count', key: 'tasks', width: 70 },
            { title: '最新任务', dataIndex: 'latest_task_status', key: 'latest', width: 90, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
            {
              title: '操作', key: 'action', width: 60, render: (_, r) => (
                <Popconfirm title="确认删除?" onConfirm={() => handleDelete(r.id)}>
                  <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                </Popconfirm>
              ),
            },
          ]}
        />
      </Card>

      <Modal title="添加企业" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} width={520}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="企业名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="aliases" label="企业别名"><Input placeholder="多个别名用逗号分隔" /></Form.Item>
          <Form.Item name="industry" label="行业" rules={[{ required: true }]}>
            <Select options={['fintech', 'ecommerce', 'tech', 'government', 'healthcare'].map((i) => ({ value: i, label: industryLabels[i] }))} />
          </Form.Item>
          <Form.Item name="domains" label="授权域名"><Input placeholder="多个域名用逗号分隔" /></Form.Item>
          <Form.Item name="ip_ranges" label="IP 范围"><Input placeholder="多个CIDR用逗号分隔" /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={selected?.name} open={!!selected} onClose={() => setSelected(null)} width={480}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="行业">{industryLabels[selected.industry] || selected.industry}</Descriptions.Item>
            <Descriptions.Item label="别名">{selected.aliases.join(', ') || '无'}</Descriptions.Item>
            <Descriptions.Item label="关联域名">{selected.domains.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="IP 范围">{selected.ip_ranges.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="排除">{selected.exclude.join(', ') || '无'}</Descriptions.Item>
            <Descriptions.Item label="任务数">{selected.task_count}</Descriptions.Item>
            {selected.notes && <Descriptions.Item label="备注">{selected.notes}</Descriptions.Item>}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Companies;
