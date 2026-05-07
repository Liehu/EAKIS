import { useEffect, useState } from 'react';
import { Card, Table, Button, Space, Select, Tag, Modal, Form, Input, Drawer, Descriptions, message, Popconfirm } from 'antd';
import { PlusOutlined, PauseCircleOutlined, PlayCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { listTasks, pauseTask, resumeTask, cancelTask, retryTask, batchCancelTasks, batchResumeTasks } from '@/api/tasks';
import type { Task, TaskStatus } from '@/types/task';

const statusColors: Record<TaskStatus, string> = {
  pending: 'default', running: 'processing', paused: 'warning', completed: 'success', failed: 'error', cancelled: 'default',
};

const TaskManagement: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailTask, setDetailTask] = useState<Task | null>(null);
  const [form] = Form.useForm();

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await listTasks({ status: statusFilter });
      setTasks(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchTasks(); }, [statusFilter]);

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
      <Card title="任务管理" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
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
        }>
        <Table size="small" loading={loading} dataSource={tasks} rowKey="task_id" pagination={{ pageSize: 20 }}
          rowSelection={{ selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys as string[]) }}
          onRow={(record) => ({ onClick: () => setDetailTask(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '任务ID', dataIndex: 'task_id', key: 'id', width: 160, ellipsis: true },
            { title: '企业', dataIndex: 'company_name', key: 'company' },
            { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: TaskStatus) => <Tag color={statusColors[v]}>{v}</Tag> },
            { title: '当前阶段', dataIndex: 'current_stage', key: 'stage', width: 120 },
            { title: '进度', key: 'progress', width: 80, render: (_, r) => `${Math.round(r.progress * 100)}%` },
            { title: '资产/漏洞', key: 'stats', width: 100, render: (_, r) => `${r.stats.assets_found} / ${r.stats.vulns_detected}` },
            { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 160, render: (v: string) => new Date(v).toLocaleString('zh-CN') },
            {
              title: '操作', key: 'action', width: 160, render: (_, r) => (
                <Space size={4}>
                  {r.status === 'running' && <Button size="small" type="text" icon={<PauseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'pause'); }} />}
                  {r.status === 'paused' && <Button size="small" type="text" icon={<PlayCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'resume'); }} />}
                  {(r.status === 'running' || r.status === 'paused') && <Button size="small" type="text" danger icon={<CloseCircleOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'cancel'); }} />}
                  {r.status === 'failed' && <Button size="small" type="text" icon={<ReloadOutlined />} onClick={(e) => { e.stopPropagation(); handleAction(r.task_id, 'retry'); }} />}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal title="新建探测任务" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} width={600}>
        <Form form={form} layout="vertical" onFinish={() => { message.success('任务创建成功'); setCreateOpen(false); form.resetFields(); }}>
          <Form.Item name="company_name" label="企业名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="industry" label="行业" rules={[{ required: true }]}>
            <Select options={[{ value: 'fintech', label: '金融科技' }, { value: 'ecommerce', label: '电商' }, { value: 'tech', label: '互联网' }, { value: 'government', label: '政务' }, { value: 'healthcare', label: '医疗' }]} />
          </Form.Item>
          <Form.Item name="domains" label="授权域名"><Input placeholder="多个域名用逗号分隔" /></Form.Item>
          <Form.Item name="pentest_enabled" label="启用渗透测试" initialValue={true}>
            <Select options={[{ value: true, label: '是' }, { value: false, label: '否' }]} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title={`任务详情: ${detailTask?.task_id}`} open={!!detailTask} onClose={() => setDetailTask(null)} width={520}>
        {detailTask && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="企业">{detailTask.company_name}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[detailTask.status]}>{detailTask.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="当前阶段">{detailTask.current_stage}</Descriptions.Item>
            <Descriptions.Item label="进度">{Math.round(detailTask.progress * 100)}%</Descriptions.Item>
            <Descriptions.Item label="发现资产">{detailTask.stats.assets_found} (确认 {detailTask.stats.assets_confirmed})</Descriptions.Item>
            <Descriptions.Item label="爬取接口">{detailTask.stats.interfaces_crawled}</Descriptions.Item>
            <Descriptions.Item label="检出漏洞">{detailTask.stats.vulns_detected} (确认 {detailTask.stats.vulns_confirmed})</Descriptions.Item>
            <Descriptions.Item label="创建时间">{new Date(detailTask.created_at).toLocaleString('zh-CN')}</Descriptions.Item>
            {detailTask.estimated_completion && <Descriptions.Item label="预计完成">{new Date(detailTask.estimated_completion).toLocaleString('zh-CN')}</Descriptions.Item>}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default TaskManagement;
