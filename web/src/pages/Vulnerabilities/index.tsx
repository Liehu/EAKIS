import { useEffect, useState } from 'react';
import { Card, Table, Select, Drawer, Descriptions, Tag, Input, Progress } from 'antd';
import { getVulnerabilities } from '@/api/vulnerabilities';
import RiskTag from '@/components/RiskTag';
import type { Vulnerability, RiskLevel } from '@/types/vulnerability';

const VulnStatusTag: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = { confirmed: 'green', false_positive: 'default', fixed: 'blue', wont_fix: 'orange' };
  return <Tag color={colors[status] || 'default'}>{status}</Tag>;
};

const Vulnerabilities: React.FC = () => {
  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | undefined>();
  const [selected, setSelected] = useState<Vulnerability | null>(null);

  const fetchVulns = async () => {
    setLoading(true);
    try {
      const res = await getVulnerabilities('task_01J9XXXXX', { severity: severityFilter });
      setVulns(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchVulns(); }, [severityFilter]);

  return (
    <div>
      <Card title="漏洞库" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Select placeholder="严重性" allowClear size="small" style={{ width: 100 }} value={severityFilter} onChange={setSeverityFilter}
            options={['critical', 'high', 'medium', 'low'].map((s) => ({ value: s, label: s }))} />
        }>
        <Table size="small" loading={loading} dataSource={vulns} rowKey="id" pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '漏洞标题', dataIndex: 'title', key: 'title', ellipsis: true },
            { title: '类型', dataIndex: 'vuln_type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '严重性', dataIndex: 'severity', key: 'severity', width: 80, render: (v: RiskLevel) => <RiskTag level={v} /> },
            { title: 'CVSS', dataIndex: 'cvss_score', key: 'cvss', width: 60, sorter: (a, b) => a.cvss_score - b.cvss_score },
            { title: 'LLM置信度', key: 'confidence', width: 90, render: (_, r) => `${(r.llm_confidence * 100).toFixed(0)}%` },
            { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <VulnStatusTag status={v} /> },
            { title: '误报风险', dataIndex: 'false_positive_risk', key: 'fp', width: 80 },
          ]}
        />
      </Card>
      <Drawer title={selected?.title} open={!!selected} onClose={() => setSelected(null)} width={640}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="漏洞类型">{selected.vuln_type}</Descriptions.Item>
            <Descriptions.Item label="严重性"><RiskTag level={selected.severity} /></Descriptions.Item>
            <Descriptions.Item label="CVSS 评分">{selected.cvss_score}</Descriptions.Item>
            <Descriptions.Item label="描述">{selected.description}</Descriptions.Item>
            <Descriptions.Item label="影响路径"><Input.TextArea value={selected.affected_path} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="测试载荷"><Input.TextArea value={selected.test_payload} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="LLM 置信度">
              <Progress percent={Math.round(selected.llm_confidence * 100)} size="small" style={{ width: 200 }} />
            </Descriptions.Item>
            <Descriptions.Item label="误报风险">{selected.false_positive_risk}</Descriptions.Item>
            <Descriptions.Item label="修复建议">{selected.remediation}</Descriptions.Item>
            <Descriptions.Item label="证据 — 请求"><Input.TextArea value={selected.evidence.request} autoSize readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} /></Descriptions.Item>
            <Descriptions.Item label="证据 — 响应码">{selected.evidence.response_code}</Descriptions.Item>
            <Descriptions.Item label="证据 — 响应片段"><Input.TextArea value={selected.evidence.response_snippet} autoSize readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} /></Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Vulnerabilities;
