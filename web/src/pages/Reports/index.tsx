import { useEffect, useState } from 'react';
import { Table, Button, Tag, Progress, Modal, Form, Select, Switch, message, Drawer, Descriptions, Empty, Spin } from 'antd';
import { DownloadOutlined, FileTextOutlined, EyeOutlined } from '@ant-design/icons';
import { listReports, generateReport, getReport } from '@/api/reports';
import { getTemplates } from '@/api/templates';
import { useTaskStore } from '@/store/taskStore';
import type { Report } from '@/api/reports';
import type { Template } from '@/types/template';
import { useRightPanelStore } from '@/store/rightPanelStore';

const statusColor: Record<string, string> = {
  completed: 'green', generating: 'blue', failed: 'red', pending: 'default',
};

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reportTemplates, setReportTemplates] = useState<Template[]>([]);
  const [form] = Form.useForm();

  // 报告内容查看
  const [viewing, setViewing] = useState<Report | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [viewLoading, setViewLoading] = useState(false);
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  const currentTask = useTaskStore((s) => s.currentTask);
  const taskId = currentTask?.task_id;

  const fetchReports = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const res = await listReports(taskId);
      setReports(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchReports(); }, [taskId]); // eslint-disable-line

  const openGenerate = async () => {
    // 加载 S4 报告模板
    try {
      const res = await getTemplates({ template_type: 'report', page: 1, page_size: 100 });
      setReportTemplates(res.data);
      const first = res.data[0];
      form.setFieldsValue({ template: first?.name || 'standard', use_llm: false });
    } catch {
      form.setFieldsValue({ template: 'standard', use_llm: false });
    }
    setGenModalOpen(true);
  };

  const handleGenerate = async () => {
    const values = await form.validateFields();
    if (!taskId) return;
    setGenerating(true);
    try {
      await generateReport(taskId, {
        format: ['markdown', 'pdf'],
        sections: ['summary', 'assets', 'interfaces', 'vulns', 'remediation'],
        language: 'zh-CN',
        template: values.template,
        use_llm: values.use_llm,
      });
      message.success('报告已生成');
      setGenModalOpen(false);
      form.resetFields();
      fetchReports();
    } catch {
      message.error('报告生成失败');
    } finally {
      setGenerating(false);
    }
  };

  const viewReport = async (r: Report) => {
    setDrawerOpen(true);
    setViewLoading(true);
    setViewing(r);
    setPanelItem('report', r as unknown as Record<string, unknown>);
    try {
      // 拉取最新详情 (含 content)
      const full = await getReport(taskId!, r.report_id);
      setViewing(full);
      setPanelItem('report', full as unknown as Record<string, unknown>);
    } catch {
      // 保留列表数据
    } finally {
      setViewLoading(false);
    }
  };

  const downloadContent = (r: Report) => {
    if (!r.content) { message.warning('报告内容为空'); return; }
    const blob = new Blob([r.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${r.report_id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>报告中心</span>
        <Button size="small" type="primary" icon={<FileTextOutlined />} onClick={openGenerate}>生成报告</Button>
      </div>
      <Table size="small" loading={loading} dataSource={reports} rowKey="report_id" pagination={{ pageSize: 20 }}
        columns={[
          { title: '报告 ID', dataIndex: 'report_id', key: 'id', width: 120, render: (v: string) => v?.slice(0, 8) },
          {
            title: '状态', dataIndex: 'status', key: 'status', width: 90,
            render: (v: string) => <Tag color={statusColor[v] || 'default'}>{v || '—'}</Tag>,
          },
          {
            title: '质量评分', key: 'quality', width: 120,
            render: (_, r) => r.quality_score ? (
              <div>
                <Progress percent={Math.round(r.quality_score.overall * 100)} size="small" style={{ width: 90 }} />
              </div>
            ) : '—',
          },
          { title: '页数', dataIndex: 'page_count', key: 'pages', width: 60 },
          { title: '字数', dataIndex: 'word_count', key: 'words', width: 80, render: (v: number) => v || '—' },
          {
            title: '耗时', key: 'duration', width: 80,
            render: (_, r) => r.generation_duration_minutes != null ? `${r.generation_duration_minutes} 分` : '—',
          },
          {
            title: '生成时间', dataIndex: 'generated_at', key: 'gen_at', width: 160,
            render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '—',
          },
          {
            title: '操作', key: 'action', width: 180,
            render: (_, r) => (
              <>
                <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => viewReport(r)}>查看</Button>
                {r.content && <Button size="small" type="link" icon={<DownloadOutlined />} onClick={() => downloadContent(r)}>MD</Button>}
                {r.files?.pdf && <Button size="small" type="link" icon={<DownloadOutlined />}>PDF</Button>}
              </>
            ),
          },
        ]}
      />

      <Modal
        title="生成报告"
        open={genModalOpen}
        onCancel={() => setGenModalOpen(false)}
        onOk={handleGenerate}
        okText="生成" cancelText="取消"
        confirmLoading={generating}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="template" label="报告模板" rules={[{ required: true, message: '请选择报告模板' }]}>
            <Select
              placeholder="选择报告模板"
              options={reportTemplates.length > 0
                ? reportTemplates.map((t) => ({ value: t.name, label: `${t.name}${t.parent_name ? ` (继承 ${t.parent_name})` : ''}` }))
                : [{ value: 'standard', label: '标准报告 (默认)' }, { value: '资产报告-标准版', label: '资产报告-标准版' }]}
            />
          </Form.Item>
          <Form.Item name="use_llm" label="LLM 执行摘要" valuePropName="checked" tooltip="使用 LLM 生成执行摘要 (可选, 失败自动降级模板模式)">
            <Switch />
          </Form.Item>
          <div style={{ color: '#64748b', fontSize: 12 }}>
            报告将聚合当前任务的资产/漏洞/接口/情报数据，按所选模板字段渲染为 Markdown。
          </div>
        </Form>
      </Modal>

      <Drawer
        title="报告详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={720}
      >
        {viewLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : viewing ? (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="报告 ID">{viewing.report_id?.slice(0, 8)}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor[viewing.status] || 'default'}>{viewing.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="质量评分">{viewing.quality_score ? `${Math.round(viewing.quality_score.overall * 100)}%` : '—'}</Descriptions.Item>
              <Descriptions.Item label="字数/页数">{viewing.word_count || 0} / {viewing.page_count || 0}</Descriptions.Item>
              {viewing.quality_score && (
                <>
                  <Descriptions.Item label="准确率">{Math.round(viewing.quality_score.accuracy * 100)}%</Descriptions.Item>
                  <Descriptions.Item label="完整性">{Math.round(viewing.quality_score.completeness * 100)}%</Descriptions.Item>
                  <Descriptions.Item label="可读性">{Math.round(viewing.quality_score.readability * 100)}%</Descriptions.Item>
                  <Descriptions.Item label="可操作性">{Math.round(viewing.quality_score.actionability * 100)}%</Descriptions.Item>
                </>
              )}
              <Descriptions.Item label="生成时间" span={2}>{viewing.generated_at ? new Date(viewing.generated_at).toLocaleString('zh-CN') : '—'}</Descriptions.Item>
            </Descriptions>

            {viewing.content ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>报告内容 (Markdown)</span>
                  <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadContent(viewing)}>下载 .md</Button>
                </div>
                <pre style={{
                  background: '#0f172a', padding: 16, borderRadius: 8,
                  fontSize: 12, overflow: 'auto', whiteSpace: 'pre-wrap',
                  maxHeight: '70vh', color: '#e2e8f0', lineHeight: 1.6,
                }}>
                  {viewing.content}
                </pre>
              </div>
            ) : (
              <Empty description={viewing.status === 'generating' ? '报告生成中...' : '报告内容为空'} />
            )}
          </>
        ) : (
          <Empty />
        )}
      </Drawer>
    </div>
  );
};

export default Reports;
