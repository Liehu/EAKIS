import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Select, Badge, Spin } from 'antd';
import {
  DashboardOutlined,
  BankOutlined,
  CloudServerOutlined,
  BugOutlined,
  ToolOutlined,
  FileTextOutlined,
  UnorderedListOutlined,
  BookOutlined,
  AppstoreOutlined,
  SettingOutlined,
  LogoutOutlined,
  CustomerServiceOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';
import { useAppStore } from '@/store/appStore';
import { useTaskStore } from '@/store/taskStore';
import { useAuthStore } from '@/store/authStore';
import { listTasks, getTask } from '@/api/tasks';
import type { Task } from '@/types/task';

/* ── 菜单数据定义 ── */

interface FlatMenuItem {
  key: string;
  icon: ReactNode;
  label: string;
  route: string;
}

interface SubMenuItem {
  key: string;
  label: string;
  route: string;
}

interface ParentMenuItem {
  key: string;
  icon: ReactNode;
  label: string;
  children: SubMenuItem[];
}

type MenuItem = FlatMenuItem | ParentMenuItem;

function isParent(item: MenuItem): item is ParentMenuItem {
  return 'children' in item && Array.isArray((item as ParentMenuItem).children);
}

const menuItems: MenuItem[] = [
  { key: 'overview', icon: <DashboardOutlined />, label: '总览', route: '/' },
  {
    key: 'taskRoot', icon: <UnorderedListOutlined />, label: '任务管理',
    children: [
      { key: 'task_scan', label: '扫描任务', route: '/tasks/scan' },
      { key: 'task_import', label: '导入任务', route: '/tasks/import' },
      { key: 'task_export', label: '导出任务', route: '/tasks/export' },
      { key: 'task_drill', label: '演练任务', route: '/tasks/drill' },
    ],
  },
  { key: 'enterprise', icon: <BankOutlined />, label: '企业管理', route: '/companies' },
  { key: 'asset', icon: <CloudServerOutlined />, label: '资产管理', route: '/assets' },
  { key: 'vulnerability', icon: <BugOutlined />, label: '漏洞管理', route: '/vulnerabilities' },
  {
    key: 'knowledgeRoot', icon: <BookOutlined />, label: '知识库管理',
    children: [
      { key: 'knowledge_vuln', label: '漏洞知识库', route: '/knowledge/vulns' },
      { key: 'knowledge_payloads', label: '字典管理', route: '/knowledge/payloads' },
      { key: 'knowledge_fingerprint', label: '指纹库', route: '/knowledge/fingerprints' },
      { key: 'knowledge_datasource', label: '数据源定义', route: '/knowledge/datasources' },
      { key: 'knowledge_handbook', label: '攻防经验手册', route: '/knowledge/handbooks' },
    ],
  },
  { key: 'tool', icon: <ToolOutlined />, label: '工具管理', route: '/tools' },
  {
    key: 'templateRoot', icon: <AppstoreOutlined />, label: '模板管理',
    children: [
      { key: 'template_task', label: '任务模板', route: '/templates/task' },
      { key: 'template_report', label: '报告模板', route: '/templates/report' },
      { key: 'template_prompt', label: '提示词', route: '/templates/prompt' },
      { key: 'template_attack', label: '可视化攻击路径', route: '/templates/attack' },
    ],
  },
  { key: 'report', icon: <FileTextOutlined />, label: '报告管理', route: '/reports' },
  {
    key: 'adminRoot', icon: <TeamOutlined />, label: '系统管理',
    children: [
      { key: 'admin_users', label: '用户管理', route: '/admin/users' },
      { key: 'admin_teams', label: '团队管理', route: '/admin/teams' },
      { key: 'admin_audit', label: '审计日志', route: '/admin/audit-logs' },
      { key: 'admin_agents', label: 'Agent 管理', route: '/agent-management' },
    ],
  },
];

/* ── 状态标签映射 ── */
const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待启动', running: '执行中', paused: '已暂停',
    completed: '已完成', failed: '已失败', cancelled: '已取消',
  };
  return map[status] || status;
};

/* ── Sidebar 组件 ── */
const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const expandedMenus = useAppStore((s) => s.expandedMenus);
  const toggleMenu = useAppStore((s) => s.toggleMenu);
  const currentTask = useTaskStore((s) => s.currentTask);
  const setCurrentTask = useTaskStore((s) => s.setCurrentTask);
  const doLogout = useAuthStore((s) => s.logout);

  // 任务选择器状态
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);

  // 加载任务列表
  useEffect(() => {
    setLoading(true);
    listTasks({ page: 1, page_size: 50 })
      .then((res) => {
        const items = (res as any).data?.items || (res as any).data || [];
        setTasks(items);
        if (items.length > 0 && !currentTask) {
          const first = items[0];
          getTask(first.task_id).then(setCurrentTask).catch(() => setCurrentTask(first));
        }
      })
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, []);

  const handleTaskChange = (taskId: string) => {
    getTask(taskId).then(setCurrentTask).catch(() => {
      const found = tasks.find((t) => t.task_id === taskId);
      if (found) setCurrentTask(found);
    });
  };

  const handleLogout = () => {
    doLogout();
    window.location.href = '/login';
  };

  const taskOptions = tasks.map((t) => ({
    value: t.task_id,
    label: t.company_name,
  }));

  // 计算当前活跃菜单 key（从 pathname 反推）
  const pathname = location.pathname;
  const activeKey = (() => {
    // 精确匹配子项
    for (const item of menuItems) {
      if (isParent(item)) {
        for (const child of item.children) {
          if (pathname === child.route || pathname.startsWith(child.route + '/')) return child.key;
        }
      } else {
        if (pathname === item.route || (item.route === '/' && pathname === '/')) return item.key;
      }
    }
    // 模糊匹配父级
    for (const item of menuItems) {
      if (isParent(item) && pathname.startsWith('/tasks')) return item.key;
    }
    return 'overview';
  })();

  // 根据当前路径自动展开对应的父菜单
  useEffect(() => {
    for (const item of menuItems) {
      if (!isParent(item)) continue;
      for (const child of item.children) {
        if (pathname === child.route || pathname.startsWith(child.route + '/')) {
          if (!expandedMenus.includes(item.key)) {
            toggleMenu(item.key);
          }
          break;
        }
      }
    }
  }, [pathname]);

  return (
    <div
      style={{
        width: collapsed ? 80 : 280,
        background: '#141422',
        color: '#e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease',
        boxShadow: '4px 0 20px rgba(0,0,0,0.15)',
        zIndex: 20,
        overflow: 'hidden',
        flexShrink: 0,
        height: '100%',
      }}
    >
      {/* Logo 区 */}
      <div style={{
        padding: collapsed ? '24px 0' : '24px 20px',
        borderBottom: '1px solid #2a2a4e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
      }}>
        {!collapsed && (
          <div style={{ fontSize: '1.1rem', fontWeight: 700, whiteSpace: 'nowrap', color: '#378ADD' }}>
            <CustomerServiceOutlined style={{ marginRight: 8 }} />
            安鉴·天穹
          </div>
        )}
        <button
          onClick={toggleSidebar}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: '1.1rem',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </button>
      </div>

      {/* 导航菜单区 */}
      <div style={{
        flex: 1,
        padding: collapsed ? '20px 0' : '20px 12px',
        overflowY: 'auto',
        overflowX: 'hidden',
      }}>
        {menuItems.map((item) => {
          if (isParent(item)) {
            const isExpanded = expandedMenus.includes(item.key);
            const isParentActive = item.children.some(
              (c) => c.key === activeKey
            );
            return (
              <div key={item.key}>
                <div
                  onClick={() => {
                    if (!collapsed) toggleMenu(item.key);
                    else navigate(item.children[0]?.route || '/');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    padding: collapsed ? '12px 0' : '10px 16px',
                    marginBottom: 4,
                    borderRadius: 12,
                    cursor: 'pointer',
                    transition: '0.2s',
                    color: isParentActive ? '#fff' : '#cbd5e6',
                    fontWeight: 500,
                    whiteSpace: 'nowrap',
                    background: isParentActive ? '#378ADD22' : 'transparent',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                  onMouseEnter={(e) => {
                    if (!isParentActive) (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
                  }}
                  onMouseLeave={(e) => {
                    if (!isParentActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
                  }}
                >
                  <span style={{ width: 24, fontSize: '1.1rem', textAlign: 'center', flexShrink: 0 }}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <>
                      <span style={{ flex: 1 }}>{item.label}</span>
                      <span style={{
                        fontSize: 10,
                        transition: 'transform 0.2s',
                        transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                        color: '#666',
                      }}>
                        ▶
                      </span>
                    </>
                  )}
                </div>
                {/* 二级菜单 */}
                {!collapsed && isExpanded && (
                  <div style={{
                    marginLeft: 38,
                    paddingLeft: 8,
                    borderLeft: '1px solid #2a2a4e',
                    marginBottom: 8,
                  }}>
                    {item.children.map((child) => (
                      <div
                        key={child.key}
                        onClick={() => navigate(child.route)}
                        style={{
                          padding: '8px 12px',
                          margin: '4px 0',
                          borderRadius: 10,
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          color: activeKey === child.key ? '#fff' : '#b9c7d9',
                          whiteSpace: 'nowrap',
                          background: activeKey === child.key ? '#378ADD33' : 'transparent',
                          transition: '0.15s',
                        }}
                        onMouseEnter={(e) => {
                          if (activeKey !== child.key) (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
                        }}
                        onMouseLeave={(e) => {
                          if (activeKey !== child.key) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
                        }}
                      >
                        {child.label}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          // flat 菜单项
          const isActive = activeKey === item.key;
          return (
            <div
              key={item.key}
              onClick={() => navigate(item.route)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: collapsed ? '12px 0' : '10px 16px',
                marginBottom: 4,
                borderRadius: 12,
                cursor: 'pointer',
                transition: '0.2s',
                color: isActive ? '#fff' : '#cbd5e6',
                fontWeight: 500,
                whiteSpace: 'nowrap',
                background: isActive ? '#378ADD22' : 'transparent',
                justifyContent: collapsed ? 'center' : 'flex-start',
              }}
              onMouseEnter={(e) => {
                if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
              }}
              onMouseLeave={(e) => {
                if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
              }}
            >
              <span style={{ width: 24, fontSize: '1.1rem', textAlign: 'center', flexShrink: 0 }}>
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
            </div>
          );
        })}
      </div>

      {/* Footer 区 */}
      <div style={{
        padding: collapsed ? '16px 0' : '12px',
        borderTop: '1px solid #2a2a4e',
        fontSize: '0.8rem',
      }}>
        {/* 任务选择器（仅展开时显示） */}
        {!collapsed && (
          <div style={{ padding: '4px 12px 12px' }}>
            <div style={{ color: '#666', fontSize: 11, marginBottom: 6 }}>当前任务</div>
            <Select
              value={currentTask?.task_id}
              style={{ width: '100%' }}
              placeholder="选择任务"
              size="small"
              options={taskOptions}
              loading={loading}
              notFoundContent={loading ? <Spin size="small" /> : '暂无任务'}
              onChange={handleTaskChange}
              dropdownStyle={{ background: '#1a1a2e' }}
            />
            {currentTask && (
              <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Badge
                  status={currentTask.status === 'running' ? 'processing' : 'default'}
                  text={(
                    <span style={{
                      fontSize: 11,
                      color: currentTask.status === 'running' ? '#52c41a' : '#888',
                    }}>
                      {statusLabel(currentTask.status)}
                    </span>
                  )}
                />
              </div>
            )}
          </div>
        )}

        {/* Footer 菜单项 */}
        <div
          onClick={() => navigate('/settings')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            padding: collapsed ? '8px 0' : '8px 12px',
            borderRadius: 10,
            cursor: 'pointer',
            color: '#94a3b8',
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: '0.15s',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
            (e.currentTarget as HTMLDivElement).style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            (e.currentTarget as HTMLDivElement).style.color = '#94a3b8';
          }}
        >
          <SettingOutlined style={{ fontSize: '0.95rem' }} />
          {!collapsed && <span>系统设置</span>}
        </div>
        <div
          onClick={handleLogout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            padding: collapsed ? '8px 0' : '8px 12px',
            borderRadius: 10,
            cursor: 'pointer',
            color: '#94a3b8',
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: '0.15s',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
            (e.currentTarget as HTMLDivElement).style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            (e.currentTarget as HTMLDivElement).style.color = '#94a3b8';
          }}
        >
          <LogoutOutlined style={{ fontSize: '0.95rem' }} />
          {!collapsed && <span>用户退出</span>}
        </div>
        <div
          onClick={() => navigate('/status')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            padding: collapsed ? '8px 0' : '8px 12px',
            borderRadius: 10,
            cursor: 'pointer',
            color: '#94a3b8',
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: '0.15s',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = '#ffffff0a';
            (e.currentTarget as HTMLDivElement).style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            (e.currentTarget as HTMLDivElement).style.color = '#94a3b8';
          }}
        >
          <CustomerServiceOutlined style={{ fontSize: '0.95rem' }} />
          {!collapsed && <span>系统状态</span>}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
