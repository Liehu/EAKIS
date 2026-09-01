import { useState } from 'react';
import { Table, Button, Space, DatePicker, Popconfirm, message, Tooltip } from 'antd';
import { DownloadOutlined, DeleteOutlined, FileExcelOutlined, FileTextOutlined, FilePdfOutlined, DatabaseOutlined } from '@ant-design/icons';
import FilterBar from '@/components/FilterBar';
import BatchActionBar from '@/components/BatchActionBar';

const { RangePicker } = DatePicker;

interface ExportRecord {
  id: string;
  file_name: string;
  type: 'enterprise_list' | 'asset_list' | 'report' | 'knowledge';
  status: 'exporting' | 'success' | 'failed';
  size: string;
  created_at: string;
  created_by: string;
}

// 类型标签语义令牌（规范 §03）：企业列表=accent · 资产列表=success · 报告=warning · 知识库=info 灰蓝
const typeConfig: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  enterprise_list: { text: '企业列表', color: 'var(--accent-color)', icon: <FileExcelOutlined /> },
  asset_list: { text: '资产列表', color: 'var(--success)', icon: <FileExcelOutlined /> },
  report: { text: '报告', color: 'var(--warning)', icon: <FilePdfOutlined /> },
  knowledge: { text: '知识库', color: 'var(--severity-info)', icon: <DatabaseOutlined /> },
};

// 导出状态徽章（规范 §06 状态徽章）：导出中=accent+脉冲点 · 成功=success · 失败=error
const exportStatusMeta: Record<ExportRecord['status'], { text: string; color: string; pulse?: boolean }> = {
  exporting: { text: '导出中', color: 'var(--accent-color)', pulse: true },
  success: { text: '成功', color: 'var(--success)' },
  failed: { text: '失败', color: 'var(--error)' },
};

/** 语义令牌徽章：10% 同色底 + 同色字（规范 §06 徽章形态，禁止 hex 徽章） */
const TokenBadge: React.FC<{ color: string; children?: React.ReactNode }> = ({ color, children }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '4px 12px',
      borderRadius: 'var(--radius-lg)',
      fontSize: 12,
      fontWeight: 500,
      lineHeight: 1.2,
      color,
      background: `color-mix(in srgb, ${color} 10%, transparent)`,
      whiteSpace: 'nowrap',
    }}
  >
    {children}
  </span>
);

// Mock 数据
const mockExportRecords: ExportRecord[] = [
  { id: 'exp_001', file_name: '华为集团_企业信息列表.xlsx', type: 'enterprise_list', status: 'success', size: '245 KB', created_at: '2026-06-01 14:30:00', created_by: 'admin' },
  { id: 'exp_002', file_name: '华为集团_下属公司信息.xlsx', type: 'enterprise_list', status: 'success', size: '128 KB', created_at: '2026-06-01 14:30:00', created_by: 'admin' },
  { id: 'exp_003', file_name: '金融集团_资产清单.xlsx', type: 'asset_list', status: 'success', size: '1.2 MB', created_at: '2026-05-31 10:15:00', created_by: 'admin' },
  { id: 'exp_004', file_name: '电商平台_资产清单.xlsx', type: 'asset_list', status: 'failed', size: '856 KB', created_at: '2026-05-30 16:45:00', created_by: 'analyst' },
  { id: 'exp_005', file_name: '金融集团_安全评估报告.pdf', type: 'report', status: 'success', size: '3.4 MB', created_at: '2026-05-29 09:20:00', created_by: 'admin' },
  { id: 'exp_006', file_name: '政务系统_渗透测试报告.pdf', type: 'report', status: 'success', size: '2.8 MB', created_at: '2026-05-28 11:30:00', created_by: 'analyst' },
  { id: 'exp_007', file_name: 'Nuclei_POC模板库导出.json', type: 'knowledge', status: 'failed', size: '512 KB', created_at: '2026-05-27 08:00:00', created_by: 'admin' },
  { id: 'exp_008', file_name: '电商企业_漏洞清单.xlsx', type: 'asset_list', status: 'success', size: '340 KB', created_at: '2026-05-26 15:30:00', created_by: 'analyst' },
  { id: 'exp_009', file_name: '集团A_企业穿透报告.pdf', type: 'report', status: 'exporting', size: '5.1 MB', created_at: '2026-05-25 10:00:00', created_by: 'admin' },
  { id: 'exp_010', file_name: '关键词库_全量导出.xlsx', type: 'knowledge', status: 'success', size: '89 KB', created_at: '2026-05-24 13:20:00', created_by: 'admin' },
  { id: 'exp_011', file_name: '电商企业_企业信息列表.xlsx', type: 'enterprise_list', status: 'success', size: '178 KB', created_at: '2026-05-23 09:45:00', created_by: 'analyst' },
  { id: 'exp_012', file_name: '政务系统_资产清单.xlsx', type: 'asset_list', status: 'exporting', size: '1.5 MB', created_at: '2026-05-22 14:10:00', created_by: 'admin' },
];

const ExportRecords: React.FC = () => {
  const [records, setRecords] = useState<ExportRecord[]>(mockExportRecords);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');

  const filteredRecords = records.filter((r) => {
    if (typeFilter && r.type !== typeFilter) return false;
    if (searchText && !r.file_name.toLowerCase().includes(searchText.toLowerCase())) return false;
    return true;
  });

  const handleDownload = (record: ExportRecord) => {
    message.success(`开始下载: ${record.file_name}`);
  };

  const handleDelete = (id: string) => {
    setRecords((prev) => prev.filter((r) => r.id !== id));
    setSelectedRowKeys((prev) => prev.filter((k) => k !== id));
    message.success('记录已删除');
  };

  const handleBatchDownload = () => {
    if (selectedRowKeys.length === 0) return;
    message.success(`正在打包下载 ${selectedRowKeys.length} 个文件...`);
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return;
    setRecords((prev) => prev.filter((r) => !selectedRowKeys.includes(r.id)));
    message.success(`已删除 ${selectedRowKeys.length} 条记录`);
    setSelectedRowKeys([]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* 页头（规范 §02） */}
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">导出记录</span>
      </div>
      <div className="eakis-page-content">
        <FilterBar
          searchPlaceholder="搜索文件名"
          onSearch={setSearchText}
          filters={[{
            key: 'type',
            label: '类型筛选',
            options: Object.entries(typeConfig).map(([k, v]) => ({ value: k, label: v.text })),
            value: typeFilter,
            onChange: setTypeFilter,
          }]}
          extra={<RangePicker size="small" placeholder={['开始日期', '结束日期']} />}
        />

        {/* 批量操作栏（规范 §06；危险操作保留 Popconfirm） */}
        <BatchActionBar
          selectedCount={selectedRowKeys.length}
          actions={[{ label: '打包下载', icon: <DownloadOutlined />, onClick: handleBatchDownload }]}
        >
          <Popconfirm
            title={`确认删除选中的 ${selectedRowKeys.length} 条记录?`}
            onConfirm={handleBatchDelete}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              批量删除
            </Button>
          </Popconfirm>
        </BatchActionBar>

        <Table
          size="small"
          dataSource={filteredRecords}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
          }}
          columns={[
            { title: '文件名', dataIndex: 'file_name', key: 'file_name', ellipsis: true, render: (v: string) => (
              <Space>
                <FileTextOutlined style={{ color: 'var(--accent-color)' }} />
                <span>{v}</span>
              </Space>
            )},
            { title: '类型', dataIndex: 'type', key: 'type', width: 110, render: (v: string) => (
              <TokenBadge color={typeConfig[v]?.color || 'var(--text-secondary)'}>
                {typeConfig[v]?.icon}
                {typeConfig[v]?.text}
              </TokenBadge>
            )},
            { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: ExportRecord['status']) => {
              const meta = exportStatusMeta[v] || exportStatusMeta.success;
              return (
                <TokenBadge color={meta.color}>
                  {meta.pulse && <span className="status-dot is-pulsing" style={{ background: meta.color }} />}
                  {meta.text}
                </TokenBadge>
              );
            }},
            { title: '大小', dataIndex: 'size', key: 'size', width: 80 },
            { title: '创建人', dataIndex: 'created_by', key: 'created_by', width: 80 },
            { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
            {
              title: '操作', key: 'action', width: 120, render: (_, r) => (
                <Space size={4}>
                  <Tooltip title="下载">
                    <Button size="small" type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(r)} />
                  </Tooltip>
                  <Popconfirm title="确认删除该记录?" onConfirm={() => handleDelete(r.id)}>
                    <Tooltip title="删除">
                      <Button size="small" type="link" danger icon={<DeleteOutlined />} />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};

export default ExportRecords;
