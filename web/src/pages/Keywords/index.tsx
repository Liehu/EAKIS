import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, Table, Tag, Button, Modal, Form, Select, Input, Statistic, Row, Col, message, AutoComplete } from 'antd';
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { getCompanyKeywords, addCompanyKeyword, deleteCompanyKeyword, generateCompanyKeywords } from '@/api/keywords';
import { searchCompanies } from '@/api/companies';
import type { Keyword, KeywordType } from '@/types/keyword';

const typeColors: Record<KeywordType, string> = { business: '#378ADD', tech: '#BA7517', entity: '#534AB7' };
const typeLabels: Record<KeywordType, string> = { business: '业务词', tech: '技术词', entity: '主体词' };

const Keywords: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [filterType, setFilterType] = useState<KeywordType | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [companyId, setCompanyId] = useState<string | null>(searchParams.get('company_id'));
  const [companyOptions, setCompanyOptions] = useState<{ value: string; label: string; id: string }[]>([]);
  const [form] = Form.useForm();

  const fetchKeywords = async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const res = await getCompanyKeywords(companyId, { type: filterType, page_size: 100 });
      setKeywords(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchKeywords(); }, [filterType, companyId]);

  const handleSearchCompany = async (q: string) => {
    if (q.length < 1) return;
    try {
      const res = await searchCompanies(q, 10);
      setCompanyOptions(res.hits.map((h) => ({ value: h.name, label: h.name, id: h.id })));
    } catch { /* ignore */ }
  };

  const handleSelectCompany = (_name: string, opt: any) => {
    setCompanyId(opt.id);
  };

  const handleGenerate = async () => {
    if (!companyId) { message.warning('请先选择企业'); return; }
    setGenerating(true);
    try {
      const res = await generateCompanyKeywords(companyId);
      message.success(`关键词生成完成，共 ${res.data.length} 条`);
      fetchKeywords();
    } catch (e: any) {
      message.error(`生成失败: ${e?.response?.data?.detail || e?.message || '请先采集情报'}`);
    } finally { setGenerating(false); }
  };

  const handleAdd = async (values: { word: string; type: KeywordType; weight: number }) => {
    await addCompanyKeyword(companyId!, { ...values, reason: '人工添加' });
    message.success('关键词已添加');
    setModalOpen(false); form.resetFields(); fetchKeywords();
  };

  const handleDelete = async (id: string) => {
    await deleteCompanyKeyword(companyId!, id);
    message.success('已删除');
    fetchKeywords();
  };

  const businessCount = keywords.filter((k) => k.type === 'business').length;
  const techCount = keywords.filter((k) => k.type === 'tech').length;
  const entityCount = keywords.filter((k) => k.type === 'entity').length;

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <AutoComplete
          style={{ width: 360 }}
          onSearch={handleSearchCompany}
          onSelect={handleSelectCompany}
          options={companyOptions}
          placeholder="搜索选择企业..."
          allowClear
        />
        {companyId && (
          <>
            <Button type="primary" icon={<ThunderboltOutlined />} loading={generating} onClick={handleGenerate}>
              从情报生成关键词
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加</Button>
          </>
        )}
      </div>

      {!companyId ? (
        <Card style={{ background: '#1a1a2e', borderColor: '#2a2a4e', textAlign: 'center', padding: 40 }}>
          <span style={{ color: '#666' }}>请先搜索并选择一个企业，查看其关键词</span>
        </Card>
      ) : (
        <>
          <Row gutter={12} style={{ marginBottom: 16 }}>
            <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>业务词</span>} value={businessCount} valueStyle={{ color: typeColors.business }} /></Card></Col>
            <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>技术词</span>} value={techCount} valueStyle={{ color: typeColors.tech }} /></Card></Col>
            <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>主体词</span>} value={entityCount} valueStyle={{ color: typeColors.entity }} /></Card></Col>
          </Row>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>企业关键词列表</span>
            <Select placeholder="筛选类型" allowClear size="small" style={{ width: 120 }} value={filterType} onChange={setFilterType}
              options={[{ value: 'business', label: '业务词' }, { value: 'tech', label: '技术词' }, { value: 'entity', label: '主体词' }]} />
          </div>
          <Table size="small" loading={loading} dataSource={keywords} rowKey="id" pagination={{ pageSize: 20 }}
            columns={[
              { title: '关键词', dataIndex: 'word', key: 'word' },
              { title: '类型', dataIndex: 'type', key: 'type', render: (type: KeywordType) => <Tag color={typeColors[type]}>{typeLabels[type]}</Tag> },
              { title: '权重', dataIndex: 'weight', key: 'weight', render: (v: number) => v.toFixed(2), sorter: (a, b) => a.weight - b.weight },
              { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (v: number) => `${(v * 100).toFixed(0)}%` },
              { title: '来源', dataIndex: 'source', key: 'source', ellipsis: true },
              { title: '操作', key: 'action', render: (_, record) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} /> },
            ]}
          />
        </>
      )}

      <Modal title="添加企业关键词" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
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
