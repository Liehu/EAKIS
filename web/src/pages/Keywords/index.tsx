import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, Table, Button, Modal, Form, Select, Input, Statistic, Row, Col, message, AutoComplete } from 'antd';
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { getCompanyKeywords, addCompanyKeyword, deleteCompanyKeyword, generateCompanyKeywords } from '@/api/keywords';
import { searchCompanies } from '@/api/companies';
import type { Keyword, KeywordType } from '@/types/keyword';

// 类型语义令牌（规范 §03/§06：10% 同色底 + 同色字）——按原色相意图映射：
// business=accent蓝 · tech=warning琥珀 · entity=brand-ai-end（AI 渐变紫端）
const typeTokens: Record<KeywordType, string> = { business: 'var(--accent-color)', tech: 'var(--warning)', entity: 'var(--brand-ai-end)' };
const typeLabels: Record<KeywordType, string> = { business: '业务词', tech: '技术词', entity: '主体词' };

// 类型标签：10% 同色底 + 同色字（形态对齐 .severity-badge：4px 12px / r12 / 12px）
const TypeTag: React.FC<{ type: KeywordType }> = ({ type }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 12, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: typeTokens[type], background: 'color-mix(in srgb, currentColor 10%, transparent)',
  }}>{typeLabels[type]}</span>
);

// 关键词胶囊（规范：accent 8% 底 + accent 字 + 999px + 4px 12px）
const KeywordCapsule: React.FC<{ text: string }> = ({ text }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center',
    padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 500,
    lineHeight: 1.2, whiteSpace: 'nowrap',
    color: 'var(--accent-color)', background: 'var(--accent-alpha-08)',
  }}>{text}</span>
);

// 数值列（权重/置信度）：20px/700 + accent（规范 §01 KPI 大数字第一层级）
const MetricValue: React.FC<{ text: string }> = ({ text }) => (
  <span style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.2, color: 'var(--accent-color)' }}>{text}</span>
);

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">关键词管理</span>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
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
      </div>
      <div className="eakis-page-content">
        {!companyId ? (
          <Card style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)', textAlign: 'center', padding: 40 }}>
            <span style={{ color: 'var(--text-muted)' }}>请先搜索并选择一个企业，查看其关键词</span>
          </Card>
        ) : (
          <>
            <Row gutter={12} style={{ marginBottom: 16 }}>
              <Col span={8}><Card size="small" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }}><Statistic title={<span style={{ color: 'var(--text-muted)' }}>业务词</span>} value={businessCount} valueStyle={{ color: typeTokens.business, fontWeight: 700 }} /></Card></Col>
              <Col span={8}><Card size="small" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }}><Statistic title={<span style={{ color: 'var(--text-muted)' }}>技术词</span>} value={techCount} valueStyle={{ color: typeTokens.tech, fontWeight: 700 }} /></Card></Col>
              <Col span={8}><Card size="small" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }}><Statistic title={<span style={{ color: 'var(--text-muted)' }}>主体词</span>} value={entityCount} valueStyle={{ color: typeTokens.entity, fontWeight: 700 }} /></Card></Col>
            </Row>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>企业关键词列表</span>
              <Select placeholder="筛选类型" allowClear size="small" style={{ width: 120 }} value={filterType} onChange={setFilterType}
                options={[{ value: 'business', label: '业务词' }, { value: 'tech', label: '技术词' }, { value: 'entity', label: '主体词' }]} />
            </div>
            <Table size="small" loading={loading} dataSource={keywords} rowKey="id" pagination={{ pageSize: 20 }}
              columns={[
                { title: '关键词', dataIndex: 'word', key: 'word', render: (v: string) => <KeywordCapsule text={v} /> },
                { title: '类型', dataIndex: 'type', key: 'type', render: (type: KeywordType) => <TypeTag type={type} /> },
                { title: '权重', dataIndex: 'weight', key: 'weight', render: (v: number) => <MetricValue text={v.toFixed(2)} />, sorter: (a, b) => a.weight - b.weight },
                { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (v: number) => <MetricValue text={`${(v * 100).toFixed(0)}%`} /> },
                { title: '来源', dataIndex: 'source', key: 'source', ellipsis: true },
                { title: '操作', key: 'action', render: (_, record) => <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} /> },
              ]}
            />
          </>
        )}
      </div>

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
