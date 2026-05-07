import { Layout, Button, Select, Badge } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAppStore } from '@/store/appStore';
import { useTaskStore } from '@/store/taskStore';

const { Header, Content } = Layout;

const AppLayout: React.FC = () => {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const currentTask = useTaskStore((s) => s.currentTask);
  const setCurrentTask = useTaskStore((s) => s.setCurrentTask);

  return (
    <Layout style={{ height: '100vh' }}>
      <Sidebar />
      <Layout>
        <Header
          style={{
            padding: '0 20px',
            background: '#141422',
            borderBottom: '1px solid #2a2a4e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 48,
            lineHeight: '48px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSidebar}
              style={{ color: '#aaa' }}
            />
            <Select
              value={currentTask?.task_id}
              style={{ width: 280 }}
              placeholder="选择任务"
              size="small"
              options={[{ value: 'task_01J9XXXXX', label: '某金融科技公司' }]}
              onChange={() => {
                setCurrentTask({
                  task_id: 'task_01J9XXXXX',
                  company_name: '某金融科技公司',
                  status: 'running',
                  current_stage: 'api_crawl',
                  progress: 0.68,
                  stats: { assets_found: 247, assets_confirmed: 189, interfaces_crawled: 1832, vulns_detected: 43, vulns_confirmed: 31 },
                  stage_details: {
                    intelligence: { status: 'completed', duration_s: 180, items: 1250 },
                    keyword_gen: { status: 'completed', keywords: 113 },
                    asset_discovery: { status: 'completed', assets: 247, confirmed: 189 },
                    api_crawl: { status: 'running', progress: 0.76, interfaces: 1832 },
                    pentest: { status: 'pending' },
                    report_gen: { status: 'pending' },
                  },
                  created_at: '2024-01-01T08:00:00Z',
                  started_at: '2024-01-01T08:01:00Z',
                  estimated_completion: '2024-01-01T16:00:00Z',
                });
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {currentTask && (
              <Badge status={currentTask.status === 'running' ? 'processing' : 'default'} text={
                <span style={{ fontSize: 12, color: currentTask.status === 'running' ? '#52c41a' : '#999' }}>
                  {currentTask.status === 'running' ? '执行中' : currentTask.status}
                </span>
              } />
            )}
          </div>
        </Header>
        <Content style={{ overflow: 'auto', padding: 20, background: '#0d0d1a' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
