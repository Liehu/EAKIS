import { useEffect, useState } from 'react';
import { Table, Button, Space, Select, Tag, Modal, Form, Input, message, Popconfirm, AutoComplete, Progress } from 'antd';
import { PlusOutlined, PauseCircleOutlined, PlayCircleOutlined, CloseCircleOutlined, ReloadOutlined, RocketOutlined } from '@ant-design/icons';
import { listTasks, createTask, startTask, getTask, pauseTask, resumeTask, cancelTask, retryTask, batchCancelTasks, batchResumeTasks } from '@/api/tasks';
import { searchCompanies } from '@/api/companies';
import { getTemplates } from '@/api/templates';
import type { Task, TaskStatus } from '@/types/task';
import StatusBadge from '@/components/StatusBadge';
import BatchActionBar from '@/components/BatchActionBar';
import { useRightPanelStore } from '@/store/rightPanelStore';

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* 页头：左标题 + 右操作区（规范 §02） */}
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">任务管理</span>
        <Space>
          <Select placeholder="状态筛选" allowClear size="small" style={{ width: 120 }} value={statusFilter} onChange={setStatusFilter}
            options={['pending', 'running', 'paused', 'completed', 'failed', 'cancelled'].map((s) => ({ value: s, label: s }))} />
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建任务</Button>
        </Space>
      </div>
      <div className="eakis-page-content">
        {/* 批量操作条（规范 §06：accent 淡底容器；危险操作保留 Popconfirm） */}
        <BatchActionBar
          selectedCount={selectedRowKeys.length}
          actions={[{ label: '批量恢复', onClick: () => handleBatch('resume') }]}
        >
          <Popconfirm title={`确认批量取消 ${selectedRowKeys.length} 个任务?`} onConfirm={() => handleBatch('cancel')}>
            <Button size="small" danger>批量取消</Button>
          </Popconfirm>
        </BatchActionBar>

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
            { title: '状态', dataIndex: 'status', key: 'status', width: 96, render: (v: TaskStatus) => <StatusBadge status={v} /> },
            { title: '当前阶段', dataIndex: 'current_stage', key: 'stage', width: 110 },
            { title: '进度', key: 'progress', width: 110, render: (_, r) => (
              <Progress percent={Math.round((r.progress || 0) * 100)} size="small" strokeColor="var(--accent-color)" />
            )},
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
                      <Button type="link" size="small" icon={<RocketOutlined />} loading={startingId === r.task_id}
                        onClick={(e) => e.stopPropagation()}>下发</Button>
                    </Popconfirm>
                  )}
                  {r.status === 'running' && <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'pause'); }}>暂停</Button>}
                  {r.status === 'paused' && <Button type="link" size="small" icon={<PlayCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'resume'); }}>恢复</Button>}
                  {(r.status === 'running' || r.status === 'paused') && <Button type="link" size="small" danger icon={<CloseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'cancel'); }}>取消</Button>}
                  {r.status === 'failed' && <Button type="link" size="small" icon={<ReloadOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'retry'); }}>重试</Button>}
                </Space>
              ),
            },
          ]}
        />
      </div>

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
