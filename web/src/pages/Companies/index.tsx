import { useEffect, useState } from 'react';
import { Table, Tag, Button, Modal, Form, Input, Select, message, Popconfirm, Space, Checkbox, Switch } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, MonitorOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import { getCompanies, createCompany, deleteCompany, updateCompany, batchEnrich } from '@/api/companies';
import type { Company } from '@/types/company';
import CompanyDetail from './Detail';

const industryLabels: Record<string, string> = { fintech: '金融科技', ecommerce: '电商', tech: '互联网', government: '政务', healthcare: '医疗', finance: '金融', security: '安全', other: '其他' };

const Companies: React.FC = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [batchEditOpen, setBatchEditOpen] = useState(false);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();

  const fetchCompanies = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const res = await getCompanies({ page: p, page_size: ps });
      setCompanies(res.data);
      setTotal(res.pagination.total);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchCompanies(1, 20); }, []);

  const [creating, setCreating] = useState(false);
  const [batchEnriching, setBatchEnriching] = useState(false);

  const handleCreate = async (values: any) => {
    setCreating(true);
    try {
      const created = await createCompany({
        ...values,
        domains: values.domains?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
        ip_ranges: values.ip_ranges?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
        aliases: values.aliases?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
        email_domains: values.email_domains?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
        keywords: values.keywords?.split(',').map((s: string) => s.trim()).filter(Boolean) || [],
      }, { enrich: values.auto_enrich !== false, provider: 'yuntu' });
      message.success(values.auto_enrich !== false ? `企业添加成功，已自动从云图采集关联企业` : '企业添加成功');
      setCreateOpen(false); form.resetFields(); fetchCompanies();
      void created;
    } catch {
      message.error('企业添加失败');
    } finally {
      setCreating(false);
    }
  };

  const handleBatchEnrich = async () => {
    setBatchEnriching(true);
    try {
      const res = await batchEnrich({ company_ids: selectedRowKeys.map(String), provider: 'yuntu' });
      const { success, failed, total_relations } = res.summary;
      message.success(`批量采集完成：成功 ${success} · 失败 ${failed} · 新增关联 ${total_relations}`);
      setSelectedRowKeys([]); fetchCompanies();
    } catch {
      message.error('批量采集失败');
    } finally {
      setBatchEnriching(false);
    }
  };

  const handleDelete = (company: Company) => {
    Modal.confirm({
      title: `删除企业 "${company.name}"?`,
      content: (
        <div>
          <p>删除后该企业及其下属单位将无法恢复。</p>
          <Checkbox defaultChecked style={{ marginTop: 8 }}>同时删除所有关联资产 ({company.task_count} 个任务相关)</Checkbox>
        </div>
      ),
      okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => { await deleteCompany(company.id); message.success('已删除'); fetchCompanies(); },
    });
  };

  const handleBatchDelete = () => {
    Modal.confirm({
      title: `批量删除 ${selectedRowKeys.length} 个企业?`,
      content: <Checkbox defaultChecked>同时删除所有关联资产</Checkbox>,
      okText: '删除', okType: 'danger', cancelText: '取消',
      onOk: async () => {
        for (const id of selectedRowKeys) { await deleteCompany(id as string); }
        message.success(`已删除 ${selectedRowKeys.length} 个企业`);
        setSelectedRowKeys([]); fetchCompanies();
      },
    });
  };

  const handleBatchEdit = async () => {
    const values = await batchForm.validateFields();
    const updateData: any = {};
    if (values.industry) updateData.industry = values.industry;
    if (values.business_status) updateData.business_status = values.business_status;
    if (values.work_id_rule !== undefined) updateData.work_id_rule = values.work_id_rule;
    if (values.notes !== undefined) updateData.notes = values.notes;
    if (values.keywords) updateData.keywords = values.keywords.split(',').map((s: string) => s.trim()).filter(Boolean);
    if (values.email_domains) updateData.email_domains = values.email_domains.split(',').map((s: string) => s.trim()).filter(Boolean);
    try {
      for (const id of selectedRowKeys) { await updateCompany(id as string, updateData); }
      message.success(`已批量修改 ${selectedRowKeys.length} 个企业`);
      setBatchEditOpen(false); batchForm.resetFields(); setSelectedRowKeys([]); fetchCompanies();
    } catch { message.error('批量修改失败'); }
  };

  const handleBatchMonitor = () => {
    message.success(`已对 ${selectedRowKeys.length} 个企业开启监控 (mock)`);
    setSelectedRowKeys([]);
  };

  if (selectedCompanyId) {
    return <CompanyDetail companyId={selectedCompanyId} onBack={() => setSelectedCompanyId(null)} onSelectCompany={(id) => setSelectedCompanyId(id)} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>企业管理</span>
        <Space>
          {selectedRowKeys.length > 0 && (
            <>
              <span style={{ color: '#378ADD', fontSize: 12 }}>已选 {selectedRowKeys.length}</span>
              <Button size="small" icon={<MonitorOutlined />} onClick={handleBatchMonitor}>监控</Button>
              <Button size="small" type="primary" ghost icon={<CloudDownloadOutlined />} loading={batchEnriching} onClick={handleBatchEnrich}>从云图采集</Button>
              <Button size="small" icon={<EditOutlined />} onClick={() => { batchForm.resetFields(); setBatchEditOpen(true); }}>批量修改</Button>
              <Button size="small" danger onClick={handleBatchDelete}>批量删除</Button>
            </>
          )}
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>添加企业</Button>
        </Space>
      </div>
      <Table size="small" loading={loading} dataSource={companies} rowKey="id"
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 家企业`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); fetchCompanies(p, ps); },
        }}
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        onRow={(record) => ({ onClick: () => setSelectedCompanyId(record.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: '企业名称', dataIndex: 'name', key: 'name', render: (v: string, r: Company) => (
            <div>
              <a onClick={(e) => { e.stopPropagation(); setSelectedCompanyId(r.id); }} style={{ color: '#378ADD' }}>{v}</a>
              {r.aliases?.length > 0 && <span style={{ color: '#666', fontSize: 11, marginLeft: 8 }}>({r.aliases.join('/')})</span>}
            </div>
          )},
          { title: '全称', key: 'full', width: 200, ellipsis: true, render: (_: any, r: Company) => r.credit_code ? r.name : '—' },
          { title: '行业', dataIndex: 'industry', key: 'industry', width: 90, render: (v: string) => <Tag>{industryLabels[v] || v || '—'}</Tag> },
          { title: '状态', dataIndex: 'business_status', key: 'status', width: 70, render: (v: string) => v ? <Tag color="green">{v}</Tag> : '—' },
          { title: '关联域名', key: 'domains', width: 180, ellipsis: true, render: (_: any, r: Company) => r.domains?.join(', ') || '—' },
          { title: '关联最近任务', key: 'latest', width: 100, render: (_: any, r: Company) => r.task_count > 0 ? <Tag color="blue">{r.latest_task_status || '—'}</Tag> : <span style={{ color: '#666' }}>无</span> },
          { title: '工号规则', dataIndex: 'work_id_rule', key: 'workid', width: 90, render: (v: string) => v || '—' },
          {
            title: '操作', key: 'action', width: 70, render: (_: any, r: Company) => (
              <Popconfirm title={`删除 "${r.name}"?`} onConfirm={() => handleDelete(r)}>
                <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
              </Popconfirm>
            ),
          },
        ]}
      />

      <Modal title="添加企业" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} confirmLoading={creating} width={560}>
        <Form form={form} layout="vertical" onFinish={handleCreate} initialValues={{ auto_enrich: true }}>
          <Form.Item name="name" label="企业名称" rules={[{ required: true }]}><Input placeholder="企业全称（云图将据此采集关联主体）" /></Form.Item>
          <Form.Item name="aliases" label="企业别名"><Input placeholder="多个用逗号分隔" /></Form.Item>
          <Form.Item name="industry" label="行业" rules={[{ required: true }]}>
            <Select options={Object.entries(industryLabels).map(([k, l]) => ({ value: k, label: l }))} />
          </Form.Item>
          <Form.Item name="domains" label="授权域名"><Input placeholder="多个用逗号分隔" /></Form.Item>
          <Form.Item name="ip_ranges" label="IP 范围"><Input placeholder="多个CIDR用逗号分隔" /></Form.Item>
          <Form.Item name="email_domains" label="邮箱后缀"><Input placeholder="company.com,多个用逗号分隔" /></Form.Item>
          <Form.Item name="work_id_rule" label="员工工号规则"><Input placeholder="如: 6位数字" /></Form.Item>
          <Form.Item name="keywords" label="业务关键词"><Input placeholder="多个用逗号分隔" /></Form.Item>
          <Form.Item name="auto_enrich" label="添加后自动从云图采集关联企业" valuePropName="checked">
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={`批量修改 ${selectedRowKeys.length} 个企业`} open={batchEditOpen} onCancel={() => setBatchEditOpen(false)} onOk={handleBatchEdit} okText="修改" cancelText="取消" width={520}>
        <Form form={batchForm} layout="vertical">
          <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>留空的字段不会被修改</div>
          <Form.Item name="industry" label="行业">
            <Select allowClear placeholder="不修改" options={Object.entries(industryLabels).map(([k, l]) => ({ value: k, label: l }))} />
          </Form.Item>
          <Form.Item name="business_status" label="存续状态">
            <Select allowClear placeholder="不修改" options={[{value:'存续',label:'存续'},{value:'注销',label:'注销'},{value:'吊销',label:'吊销'},{value:'迁出',label:'迁出'}]} />
          </Form.Item>
          <Form.Item name="work_id_rule" label="工号规则"><Input placeholder="留空不修改" /></Form.Item>
          <Form.Item name="email_domains" label="邮箱后缀"><Input placeholder="留空不修改" /></Form.Item>
          <Form.Item name="keywords" label="关键词"><Input placeholder="留空不修改, 多个用逗号分隔" /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} placeholder="留空不修改" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Companies;
