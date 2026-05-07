import { useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  KeyOutlined,
  CloudServerOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  BugOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useAppStore } from '@/store/appStore';

const { Sider } = Layout;

const coreMenuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览仪表盘' },
  { key: '/keywords', icon: <KeyOutlined />, label: '关键词生成' },
  { key: '/assets', icon: <CloudServerOutlined />, label: '资产关联' },
  { key: '/interfaces', icon: <ApiOutlined />, label: '接口爬取' },
  { key: '/pentest', icon: <ThunderboltOutlined />, label: '自动渗透' },
];

const outputMenuItems = [
  { key: '/reports', icon: <FileTextOutlined />, label: '报告中心' },
  { key: '/vulnerabilities', icon: <BugOutlined />, label: '漏洞库' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);

  const selectedKey = '/' + location.pathname.split('/').filter(Boolean)[0];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      trigger={null}
      width={220}
      style={{
        background: '#141422',
        borderRight: '1px solid #2a2a4e',
      }}
    >
      <div
        style={{
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 16px',
          borderBottom: '1px solid #2a2a4e',
        }}
      >
        <div style={{ fontSize: 16, fontWeight: 600, color: '#378ADD', whiteSpace: 'nowrap' }}>
          {collapsed ? 'AS' : 'AttackScope AI'}
        </div>
      </div>
      {!collapsed && (
        <div style={{ padding: '8px 16px 4px', fontSize: 10, color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          核心流程
        </div>
      )}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={coreMenuItems}
        onClick={({ key }) => navigate(key)}
        style={{ background: 'transparent', borderInlineEnd: 'none' }}
      />
      {!collapsed && (
        <div style={{ padding: '8px 16px 4px', fontSize: 10, color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          输出管理
        </div>
      )}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={outputMenuItems}
        onClick={({ key }) => navigate(key)}
        style={{ background: 'transparent', borderInlineEnd: 'none' }}
      />
    </Sider>
  );
};

export default Sidebar;
