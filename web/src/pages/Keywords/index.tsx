import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Select, Input, Statistic, Row, Col, message } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { getKeywords, addKeyword, deleteKeyword } from '@/api/keywords';
import type { Keyword, KeywordType } from '@/types/keyword';

const typeColors: Record<KeywordType, string> = { business: '#378ADD', tech: '#BA7517', entity: '#534AB7' };
const typeLabels: Record<KeywordType, string> = { business: '业务词', tech: '技术词', entity: '主体词' };

const Keywords: React.FC = () => {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<KeywordType | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchKeywords = async () => {
    setLoading(true);
    try {
      const res = await getKeywords('task_01J9XXXXX', { type: filterType });
      setKeywords(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchKeywords(); }, [filterType]);

  const handleAdd = async (values: { word: string; type: KeywordType; weight: number }) => {
    await addKeyword('task_01J9XXXXX', { ...values, reason: '人工添加' });
    message.success('关键词已添加');
    setModalOpen(false);
    form.resetFields();
    fetchKeywords();
  };

  const handleDelete = async (id: string) => {
    await deleteKeyword('task_01J9XXXXX', id);
    message.success('已删除');
    fetchKeywords();
  };

  const businessCount = keywords.filter((k) => k.type === 'business').length;
  const techCount = keywords.filter((k) => k.type === 'tech').length;
  const entityCount = keywords.filter((k) => k.type === 'entity').length;

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>业务词</span>} value={businessCount} valueStyle={{ color: typeColors.business }} /></Card></Col>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>技术词</span>} value={techCount} valueStyle={{ color: typeColors.tech }} /></Card></Col>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>主体词</span>} value={entityCount} valueStyle={{ color: typeColors.entity }} /></Card></Col>
      </Row>
      <Card title="关键词列表" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Select placeholder="筛选类型" allowClear size="small" style={{ width: 120 }} value={filterType} onChange={setFilterType}
              options={[{ value: 'business', label: '业务词' }, { value: 'tech', label: '技术词' }, { value: 'entity', label: '主体词' }]} />
            <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加</Button>
          </Space>
        }>
        <Table size="small" loading={loading} dataSource={keywords} rowKey="id" pagination={{ pageSize: 20 }}
          columns={[
            { title: '关键词', dataIndex: 'word', key: 'word' },
            { title: '类型', dataIndex: 'type', key: 'type', render: (type: KeywordType) => <Tag color={typeColors[type]}>{typeLabels[type]}</Tag> },
            { title: '权重', dataIndex: 'weight', key: 'weight', render: (v: number) => v.toFixed(2), sorter: (a, b) => a.weight - b.weight },
            { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (v: number) => `${(v * 100).toFixed(0)}%` },
            { title: '来源', dataIndex: 'source', key: 'source', ellipsis: true },
            { title: '已用于DSL', dataIndex: 'used_in_dsl', key: 'used_in_dsl', render: (v: boolean) => v ? '是' : '否' },
            { title: '操作', key: 'action', render: (_, record) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} /> },
          ]}
        />
      </Card>
      <Modal title="添加关键词" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="word" label="关键词" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'business', label: '业务词' }, { value: 'tech', label: '技术词' }, { value: 'entity', label: '主体词' }]} />
          </Form.Item>
          <Form.Item name="weight" label="权重" initialValue={0.8} rules={[{ required: true }]}><Input type="number" min={0} max={1} step={0.05} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Keywords;
