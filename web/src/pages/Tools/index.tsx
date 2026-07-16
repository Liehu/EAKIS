import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Modal, Form, Input, Drawer, Descriptions, Tabs, message, Space, Empty, Spin } from 'antd';
import { PlayCircleOutlined, ToolOutlined, HistoryOutlined } from '@ant-design/icons';
import { getTools, runTool, getToolExecutions } from '@/api/tools';
import type { ToolInfo, ToolExecution, RunToolRequest } from '@/types/tool';
import { useRightPanelStore } from '@/store/rightPanelStore';

const categoryLabel: Record<string, string> = {
  recon: '侦察', dns: 'DNS', portscan: '端口扫描', vulnscan: '漏洞扫描', cert: '证书查询',
};
const categoryColor: Record<string, string> = {
  recon: 'blue', dns: 'cyan', portscan: 'orange', vulnscan: 'red', cert: 'gold',
};
const statusColor: Record<string, string> = {
  success: 'green', failed: 'red', timeout: 'orange', unavailable: 'default', invalid_input: 'volcano',
};

const ToolManagement: React.FC = () => {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [activeTool, setActiveTool] = useState<ToolInfo | null>(null);
  const [form] = Form.useForm();
  const setPanelItem = useRightPanelStore((s) => s.setItem);

  // 执行历史
  const [history, setHistory] = useState<ToolExecution[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [execDetail, setExecDetail] = useState<ToolExecution | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const [tab, setTab] = useState('tools');

  const fetchTools = async () => {
    setLoading(true);
    try { setTools(await getTools()); } catch { /* ignore */ } finally { setLoading(false); }
  };

  const fetchHistory = async (p = historyPage) => {
    try {
      const res = await getToolExecutions({ page: p, page_size: 20 });
      setHistory(res.data); setHistoryTotal(res.pagination.total);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchTools(); }, []);
  useEffect(() => { if (tab === 'history') fetchHistory(historyPage); }, [tab, historyPage]); // eslint-disable-line

  const openRun = (tool: ToolInfo) => {
    setActiveTool(tool);
    form.resetFields();
    // 预填输入参数
    const inputs: Record<string, string> = {};
    tool.params.forEach((p) => { if (p.input_type === 'domain') inputs[p.name] = ''; });
    form.setFieldsValue({ inputs });
    setRunModalOpen(true);
  };

  const handleRun = async () => {
    if (!activeTool) return;
    const values = await form.validateFields();
    setRunning(true);
    try {
      const inputs: Record<string, string | string[]> = {};
      activeTool.params.forEach((p) => {
        const v = values.inputs?.[p.name];
        if (v) inputs[p.name] = p.multiple ? String(v).split(/[\n,\s]+/).filter(Boolean) : v;
      });
      const req: RunToolRequest = { inputs };
      if (values.timeout) req.timeout = Number(values.timeout);
      const result = await runTool(activeTool.name, req);
      if (result.status === 'unavailable') {
        message.warning(`工具 ${activeTool.binary} 未安装 (${result.error})`);
      } else if (result.status === 'success') {
        const parsedArr = Array.isArray(result.parsed) ? result.parsed : [];
        message.success(`${activeTool.name} 执行成功，返回 ${parsedArr.length} 条结果 (${result.duration_s}s)`);
      } else if (result.status === 'invalid_input') {
        message.error(`输入被拒: ${result.error}`);
      } else {
        message.warning(`${activeTool.name}: ${result.status} ${result.error || ''}`);
      }
      setRunModalOpen(false);
    } catch {
      message.error('执行失败');
    } finally {
      setRunning(false);
    }
  };

  // ── 工具列表 Tab ──
  const toolsTab = (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
      {tools.map((t) => (
        <Card key={t.name} size="small" style={{ background: '#141422', borderColor: '#2a2a4e' }}
          actions={[
            <Button type="link" size="small" icon={<PlayCircleOutlined />} disabled={!t.enabled}
              onClick={() => openRun(t)}>{t.enabled ? '执行' : '未启用'}</Button>,
            <Button size="small" type="link" onClick={(e) => { e.stopPropagation(); setPanelItem('tool', t as unknown as Record<string, unknown>, 'info'); }}>详情</Button>,
          ]}>
          <Card.Meta
            title={<Space><ToolOutlined /><span style={{ color: '#e2e8f0' }}>{t.name}</span><Tag color={categoryColor[t.category]}>{categoryLabel[t.category]}</Tag></Space>}
            description={
              <div>
                <div style={{ color: '#94a3b8', fontSize: 12, minHeight: 32 }}>{t.description}</div>
                <div style={{ marginTop: 8 }}>
                  <span style={{ color: '#64748b', fontSize: 11 }}>二进制: {t.binary}</span>
                  <span style={{ color: '#64748b', fontSize: 11, marginLeft: 12 }}>参数: {t.params.map((p) => p.name).join(', ') || '无'}</span>
                </div>
              </div>
            }
          />
        </Card>
      ))}
    </div>
  );

  // ── 执行历史 Tab ──
  const historyTab = (
    <Table size="small" dataSource={history} rowKey="id"
      pagination={{ current: historyPage, pageSize: 20, total: historyTotal, onChange: setHistoryPage }}
      onRow={(r) => ({ onClick: () => { setExecDetail(r); setDrawerOpen(true); setPanelItem('tool', r as unknown as Record<string, unknown>, 'execution'); }, style: { cursor: 'pointer' } })}
      columns={[
        { title: '工具', dataIndex: 'tool_name', key: 'tool', width: 110 },
        { title: '类别', dataIndex: 'category', key: 'cat', width: 90, render: (v: string) => v ? <Tag color={categoryColor[v]}>{categoryLabel[v] || v}</Tag> : '—' },
        { title: '输入', dataIndex: 'inputs', key: 'inputs', ellipsis: true, render: (v: object) => JSON.stringify(v).slice(0, 60) },
        { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColor[v] || 'default'}>{v}</Tag> },
        { title: '耗时', dataIndex: 'duration_s', key: 'dur', width: 70, render: (v: number) => v != null ? `${v}s` : '—' },
        { title: '结果数', key: 'cnt', width: 70, render: (_: unknown, r: ToolExecution) => Array.isArray(r.parsed) ? r.parsed.length : '—' },
        { title: '时间', dataIndex: 'created_at', key: 'time', width: 150, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '—' },
      ]}
    />
  );

  return (
    <div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'tools', label: <span><ToolOutlined /> 工具列表 ({tools.length})</span> },
        { key: 'history', label: <span><HistoryOutlined /> 执行历史</span> },
      ]} />
      {loading ? <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div> : tab === 'tools' ? toolsTab : historyTab}

      {/* 执行工具 Modal */}
      <Modal title={`执行 ${activeTool?.name}`} open={runModalOpen} onCancel={() => setRunModalOpen(false)}
        onOk={handleRun} okText="执行" cancelText="取消" confirmLoading={running} width={520}>
        {activeTool && (
          <Form form={form} layout="vertical">
            <div style={{ marginBottom: 12, color: '#94a3b8', fontSize: 12 }}>{activeTool.description}</div>
            {activeTool.params.map((p) => (
              <Form.Item key={p.name} name={['inputs', p.name]} label={`${p.name} (${p.input_type}${p.required ? ', 必填' : ''})`} rules={p.required ? [{ required: true, message: `请输入 ${p.name}` }] : []}>
                <Input.TextArea rows={p.multiple ? 3 : 1} placeholder={p.multiple ? `多${p.input_type}, 换行或逗号分隔` : `输入${p.input_type}, 如 example.com`} />
              </Form.Item>
            ))}
            <Form.Item name="timeout" label="超时 (秒)">
              <Input type="number" placeholder={String(activeTool.default_timeout)} />
            </Form.Item>
            <div style={{ color: '#64748b', fontSize: 11 }}>
              输入经白名单校验防注入 (domain/ip/url 正则), 恶意输入将被拒绝。
            </div>
          </Form>
        )}
      </Modal>

      {/* 执行详情 Drawer */}
      <Drawer title="执行详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={640}>
        {execDetail ? (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="工具">{execDetail.tool_name}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColor[execDetail.status]}>{execDetail.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="退出码">{execDetail.exit_code ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="耗时">{execDetail.duration_s != null ? `${execDetail.duration_s}s` : '—'}</Descriptions.Item>
              <Descriptions.Item label="输入"><pre style={{ margin: 0 }}>{JSON.stringify(execDetail.inputs, null, 2)}</pre></Descriptions.Item>
              {execDetail.error && <Descriptions.Item label="错误">{execDetail.error}</Descriptions.Item>}
            </Descriptions>
            {Array.isArray(execDetail.parsed) && execDetail.parsed.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>解析结果 ({execDetail.parsed.length} 条)</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto', maxHeight: 300 }}>
                  {JSON.stringify(execDetail.parsed.slice(0, 20), null, 2)}
                </pre>
              </div>
            )}
            {execDetail.stdout && (
              <div style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 8, color: '#94a3b8', fontSize: 12 }}>原始输出</div>
                <pre style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, fontSize: 11, overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap' }}>{execDetail.stdout.slice(0, 5000)}</pre>
              </div>
            )}
          </>
        ) : <Empty />}
      </Drawer>
    </div>
  );
};

export default ToolManagement;
