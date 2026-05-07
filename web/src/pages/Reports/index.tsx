import { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Progress, Modal, Form, Select, message } from 'antd';
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { listReports, generateReport } from '@/api/reports';
import type { Report } from '@/api/reports';

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await listReports('task_01J9XXXXX');
      setReports(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchReports(); }, []);

  const handleGenerate = async (values: { template: string }) => {
    await generateReport('task_01J9XXXXX', {
      format: ['markdown', 'pdf'],
      sections: ['summary', 'assets', 'interfaces', 'vulns', 'remediation'],
      language: 'zh-CN',
      template: values.template as 'standard',
    });
    message.success('报告生成已触发');
    setGenModalOpen(false);
    form.resetFields();
    fetchReports();
  };

  return (
    <div>
      <Card title="报告中心" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={<Button size="small" type="primary" icon={<FileTextOutlined />} onClick={() => setGenModalOpen(true)}>生成报告</Button>}>
        <Table size="small" loading={loading} dataSource={reports} rowKey="report_id" pagination={{ pageSize: 20 }}
          columns={[
            { title: '报告 ID', dataIndex: 'report_id', key: 'id' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'completed' ? 'green' : 'blue'}>{v}</Tag> },
            { title: '质量评分', key: 'quality', render: (_, r) => r.quality_score ? <Progress percent={Math.round(r.quality_score.overall * 100)} size="small" style={{ width: 100 }} /> : '-' },
            { title: '页数', dataIndex: 'page_count', key: 'pages', width: 60 },
            { title: '字数', dataIndex: 'word_count', key: 'words', width: 80 },
            { title: '生成耗时', key: 'duration', width: 80, render: (_, r) => `${r.generation_duration_minutes} 分钟` },
            { title: '下载', key: 'download', render: (_, r) => (
              <span>
                {r.files?.pdf && <Button size="small" type="link" icon={<DownloadOutlined />}>PDF</Button>}
                {r.files?.markdown && <Button size="small" type="link" icon={<DownloadOutlined />}>MD</Button>}
              </span>
            )},
          ]}
        />
      </Card>
      <Modal title="生成报告" open={genModalOpen} onCancel={() => setGenModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item name="template" label="报告模板" initialValue="standard" rules={[{ required: true }]}>
            <Select options={[{ value: 'standard', label: '标准报告' }, { value: 'detailed', label: '详细报告' }, { value: 'executive', label: '高管摘要' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Reports;
