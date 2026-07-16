import { useState } from 'react';
import { Card, Table, Button, Space, Tag, Select, DatePicker, Input, Popconfirm, message, Tooltip } from 'antd';
import { DownloadOutlined, DeleteOutlined, SearchOutlined, FileExcelOutlined, FileTextOutlined, FilePdfOutlined, DatabaseOutlined } from '@ant-design/icons';

const { RangePicker } = DatePicker;

interface ExportRecord {
  id: string;
  file_name: string;
  type: 'enterprise_list' | 'asset_list' | 'report' | 'knowledge';
  size: string;
  created_at: string;
  created_by: string;
}

const typeConfig: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  enterprise_list: { text: '企业列表', color: 'blue', icon: <FileExcelOutlined /> },
  asset_list: { text: '资产列表', color: 'green', icon: <FileExcelOutlined /> },
  report: { text: '报告', color: 'orange', icon: <FilePdfOutlined /> },
  knowledge: { text: '知识库', color: 'purple', icon: <DatabaseOutlined /> },
};

// Mock 数据
const mockExportRecords: ExportRecord[] = [
  { id: 'exp_001', file_name: '华为集团_企业信息列表.xlsx', type: 'enterprise_list', size: '245 KB', created_at: '2026-06-01 14:30:00', created_by: 'admin' },
  { id: 'exp_002', file_name: '华为集团_下属公司信息.xlsx', type: 'enterprise_list', size: '128 KB', created_at: '2026-06-01 14:30:00', created_by: 'admin' },
  { id: 'exp_003', file_name: '金融集团_资产清单.xlsx', type: 'asset_list', size: '1.2 MB', created_at: '2026-05-31 10:15:00', created_by: 'admin' },
  { id: 'exp_004', file_name: '电商平台_资产清单.xlsx', type: 'asset_list', size: '856 KB', created_at: '2026-05-30 16:45:00', created_by: 'analyst' },
  { id: 'exp_005', file_name: '金融集团_安全评估报告.pdf', type: 'report', size: '3.4 MB', created_at: '2026-05-29 09:20:00', created_by: 'admin' },
  { id: 'exp_006', file_name: '政务系统_渗透测试报告.pdf', type: 'report', size: '2.8 MB', created_at: '2026-05-28 11:30:00', created_by: 'analyst' },
  { id: 'exp_007', file_name: 'Nuclei_POC模板库导出.json', type: 'knowledge', size: '512 KB', created_at: '2026-05-27 08:00:00', created_by: 'admin' },
  { id: 'exp_008', file_name: '电商企业_漏洞清单.xlsx', type: 'asset_list', size: '340 KB', created_at: '2026-05-26 15:30:00', created_by: 'analyst' },
  { id: 'exp_009', file_name: '集团A_企业穿透报告.pdf', type: 'report', size: '5.1 MB', created_at: '2026-05-25 10:00:00', created_by: 'admin' },
  { id: 'exp_010', file_name: '关键词库_全量导出.xlsx', type: 'knowledge', size: '89 KB', created_at: '2026-05-24 13:20:00', created_by: 'admin' },
  { id: 'exp_011', file_name: '电商企业_企业信息列表.xlsx', type: 'enterprise_list', size: '178 KB', created_at: '2026-05-23 09:45:00', created_by: 'analyst' },
  { id: 'exp_012', file_name: '政务系统_资产清单.xlsx', type: 'asset_list', size: '1.5 MB', created_at: '2026-05-22 14:10:00', created_by: 'admin' },
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
    <div>
      <Card
        title="导出记录"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Select
              placeholder="类型筛选"
              allowClear
              size="small"
              style={{ width: 120 }}
              value={typeFilter}
              onChange={setTypeFilter}
              options={Object.entries(typeConfig).map(([k, v]) => ({ value: k, label: v.text }))}
            />
            <RangePicker size="small" placeholder={['开始日期', '结束日期']} />
            <Input
              placeholder="搜索文件名"
              size="small"
              allowClear
              prefix={<SearchOutlined />}
              style={{ width: 180 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </Space>
        }
      >
        {/* 批量操作栏 */}
        {selectedRowKeys.length > 0 && (
          <div style={{
            marginBottom: 12,
            padding: '6px 12px',
            background: '#0d1528',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
          }}>
            <span style={{ color: '#aaa' }}>已选 {selectedRowKeys.length} 项</span>
            <Button size="small" type="primary" icon={<DownloadOutlined />} onClick={handleBatchDownload}>
              打包下载
            </Button>
            <Popconfirm
              title={`确认删除选中的 ${selectedRowKeys.length} 条记录?`}
              onConfirm={handleBatchDelete}
            >
              <Button size="small" danger icon={<DeleteOutlined />}>
                批量删除
              </Button>
            </Popconfirm>
          </div>
        )}

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
                <FileTextOutlined style={{ color: '#378ADD' }} />
                <span>{v}</span>
              </Space>
            )},
            { title: '类型', dataIndex: 'type', key: 'type', width: 100, render: (v: string) => (
              <Tag color={typeConfig[v]?.color} icon={typeConfig[v]?.icon}>
                {typeConfig[v]?.text}
              </Tag>
            )},
            { title: '大小', dataIndex: 'size', key: 'size', width: 80 },
            { title: '创建人', dataIndex: 'created_by', key: 'created_by', width: 80 },
            { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
            {
              title: '操作', key: 'action', width: 120, render: (_, r) => (
                <Space size={4}>
                  <Tooltip title="下载">
                    <Button size="small" type="text" icon={<DownloadOutlined />} onClick={() => handleDownload(r)} />
                  </Tooltip>
                  <Popconfirm title="确认删除该记录?" onConfirm={() => handleDelete(r.id)}>
                    <Tooltip title="删除">
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ExportRecords;
