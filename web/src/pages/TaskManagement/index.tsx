import { useEffect, useState } from 'react';
import { Table, Button, Space, Select, Tag, Modal, Form, Input, message, Popconfirm, AutoComplete } from 'antd';
import { PlusOutlined, PauseCircleOutlined, PlayCircleOutlined, CloseCircleOutlined, ReloadOutlined, RocketOutlined } from '@ant-design/icons';
import { listTasks, createTask, startTask, getTask, pauseTask, resumeTask, cancelTask, retryTask, batchCancelTasks, batchResumeTasks } from '@/api/tasks';
import { searchCompanies } from '@/api/companies';
import { getTemplates } from '@/api/templates';
import type { Task, TaskStatus } from '@/types/task';
import { useRightPanelStore } from '@/store/rightPanelStore';

const statusColors: Record<TaskStatus, string> = {
  pending: 'default', running: 'processing', paused: 'warning', completed: 'success', failed: 'error', cancelled: 'default',
};

const taskTypeLabels: Record<string, string> = {
  enterprise_penetration: '企业渗透', asset_detection: '资产探测', risk_assessment: '风险评估', company_info_collection: '企业信息采集',
};

const TaskManagement: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [companyOptions, setCompanyOptions] = useState<{ value: string; label: string; companyId?: string }[]>([]);
  const [taskTemplates, setTaskTemplates] = useState<any[]>([]);
  const setPanelItem = useRightPanelStore((s) => s.setItem);
  const [form] = Form.useForm();

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await listTasks({ status: statusFilter });
      setTasks(res.data || []);
    } catch (e: any) {
      console.error('fetchTasks error:', e);
      message.error(`加载任务失败: ${e?.message || '未知错误'}`);
      setTasks([]);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchTasks(); }, [statusFilter]);

  useEffect(() => {
    // 加载任务模板供创建时选择
    getTemplates({ template_type: 'task' }).then((res) => setTaskTemplates(res.data || [])).catch(() => {});
  }, []);

  const handleSearchCompany = async (q: string) => {
    if (q.length < 1) return;
    try {
      const res = await searchCompanies(q, 10);
      setCompanyOptions(res.hits.map((h) => ({ value: h.name, label: h.name, companyId: h.id })));
    } catch { /* ignore */ }
  };

  const handleCreate = async (values: any) => {
    setCreating(true);
    try {
      const matched = companyOptions.find((c) => c.value === values.company_name);
      const config: any = {};
      // 套用模板配置
      if (values.template_id) {
        const tpl = taskTemplates.find((t) => t.id === values.template_id);
        if (tpl?.content) Object.assign(config, tpl.content);
      }
      await createTask({
        task_type: values.task_type || 'company_info_collection',
        company_name: values.company_name,
        company_id: matched?.companyId,
        industry: values.industry,
        authorized_scope: { domains: values.domains?.split(',').map((s: string) => s.trim()).filter(Boolean) || [], ip_ranges: [], exclude: [] },
        config,
      });
      message.success('任务创建成功');
      setCreateOpen(false); form.resetFields(); fetchTasks();
    } catch {
      message.error('任务创建失败');
    } finally { setCreating(false); }
  };

  const handleStart = async (taskId: string) => {
    setStartingId(taskId);
    try {
      await startTask(taskId);
      message.success('任务执行完成');
      fetchTasks();
    } catch (e: any) {
      message.error(`任务执行失败: ${e?.response?.data?.detail || e?.message || '未知错误'}`);
    } finally { setStartingId(null); }
  };

  const handleAction = async (taskId: string, action: 'pause' | 'resume' | 'cancel' | 'retry') => {
    const fn = { pause: pauseTask, resume: resumeTask, cancel: cancelTask, retry: retryTask }[action];
    await fn(taskId);
    message.success(`已${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : action === 'cancel' ? '取消' : '重试'}`);
    fetchTasks();
  };

  const handleBatch = async (action: 'cancel' | 'resume') => {
    if (selectedRowKeys.length === 0) return;
    const fn = action === 'cancel' ? batchCancelTasks : batchResumeTasks;
    await fn(selectedRowKeys);
    message.success(`已批量${action === 'cancel' ? '取消' : '恢复'} ${selectedRowKeys.length} 个任务`);
    setSelectedRowKeys([]);
    fetchTasks();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>任务管理</span>
        <Space>
          <Select placeholder="状态筛选" allowClear size="small" style={{ width: 120 }} value={statusFilter} onChange={setStatusFilter}
            options={['pending', 'running', 'paused', 'completed', 'failed', 'cancelled'].map((s) => ({ value: s, label: s }))} />
          {selectedRowKeys.length > 0 && (
            <>
              <Popconfirm title={`确认批量取消 ${selectedRowKeys.length} 个任务?`} onConfirm={() => handleBatch('cancel')}>
                <Button size="small" danger>批量取消</Button>
              </Popconfirm>
              <Button size="small" onClick={() => handleBatch('resume')}>批量恢复</Button>
            </>
          )}
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建任务</Button>
        </Space>
      </div>
      <Table size="small" loading={loading} dataSource={tasks} rowKey="task_id" pagination={{ pageSize: 20 }}
        rowSelection={{ selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys as string[]) }}
        onRow={(record) => ({ onClick: async () => {
          // 请求完整任务详情（含 stats + company_id），推入右侧面板
          try {
            const detail = await getTask(record.task_id);
            setPanelItem('task', detail as unknown as Record<string, unknown>);
          } catch {
            setPanelItem('task', record as unknown as Record<string, unknown>);
          }
        }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '任务ID', dataIndex: 'task_id', key: 'id', width: 140, ellipsis: true },
          { title: '企业', dataIndex: 'company_name', key: 'company', ellipsis: true },
          { title: '类型', key: 'type', width: 100, render: (_: any, r: any) => {
            const tt = r.config?.task_type || r.metadata?.task_type || 'enterprise_penetration';
            return <Tag>{taskTypeLabels[tt] || tt}</Tag>;
          }},
          { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: TaskStatus) => <Tag color={statusColors[v]}>{v}</Tag> },
          { title: '当前阶段', dataIndex: 'current_stage', key: 'stage', width: 110 },
          { title: '进度', key: 'progress', width: 70, render: (_, r) => `${Math.round(r.progress * 100)}%` },
          { title: '资产/漏洞', key: 'stats', width: 90, render: (_, r) => {
            const s = r.stats || {};
            return `${s.assets_found || 0} / ${s.vulns_detected || 0}`;
          }},
          { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 145, render: (v: string) => v?.slice(0, 16).replace('T', ' ') },
          {
            title: '操作', key: 'action', width: 170, render: (_, r) => (
              <Space size={4}>
                {r.status === 'pending' && (
                  <Popconfirm title="确认下发执行此任务？" onConfirm={() => handleStart(r.task_id)}>
                    <Button size="small" type="primary" ghost icon={<RocketOutlined />} loading={startingId === r.task_id}
                      onClick={(e) => e.stopPropagation()}>下发</Button>
                  </Popconfirm>
                )}
                {r.status === 'running' && <Button size="small" type="text" icon={<PauseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'pause'); }} />}
                {r.status === 'paused' && <Button size="small" type="text" icon={<PlayCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'resume'); }} />}
                {(r.status === 'running' || r.status === 'paused') && <Button size="small" type="text" danger icon={<CloseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'cancel'); }} />}
                {r.status === 'failed' && <Button size="small" type="text" icon={<ReloadOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'retry'); }} />}
              </Space>
            ),
          },
        ]}
      />

      <Modal title="新建任务" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} confirmLoading={creating} width={600}>
        <Form form={form} layout="vertical" onFinish={handleCreate} initialValues={{ task_type: 'company_info_collection' }}>
          <Form.Item name="task_type" label="任务类型" rules={[{ required: true }]}>
            <Select options={Object.entries(taskTypeLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="company_name" label="企业名称（搜索选择已有企业，或输入新企业）" rules={[{ required: true }]}>
            <AutoComplete onSearch={handleSearchCompany} options={companyOptions} placeholder="输入企业名称搜索..." />
          </Form.Item>
          <Form.Item name="template_id" label="任务模板（套用模块配置）">
            <Select allowClear placeholder="不套用模板" options={taskTemplates.map((t) => ({ value: t.id, label: t.name }))} />
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Select allowClear options={[{ value: 'fintech', label: '金融科技' }, { value: 'ecommerce', label: '电商' }, { value: 'tech', label: '互联网' }, { value: 'government', label: '政务' }, { value: 'healthcare', label: '医疗' }, { value: 'security', label: '安全' }, { value: 'telecom', label: '通信' }, { value: 'other', label: '其他' }]} />
          </Form.Item>
          <Form.Item name="domains" label="授权域名"><Input placeholder="多个域名用逗号分隔" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TaskManagement;
