import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
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
  RightOutlined,
  MonitorOutlined,
  BulbOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';
import { useAppStore } from '@/store/appStore';
import { useTaskStore } from '@/store/taskStore';
import { useAuthStore } from '@/store/authStore';
import { useThemeStore, type ThemePreference } from '@/store/themeStore';
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
      { key: 'task_list', label: '全部任务', route: '/tasks' },
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

/* ── 主题三态切换（system → light → dark，图标均已核验存在于 @ant-design/icons v6） ── */
const THEME_META: Record<ThemePreference, { icon: ReactNode; title: string; label: string }> = {
  system: { icon: <MonitorOutlined />, title: '主题：跟随系统', label: '跟随系统' },
  light: { icon: <BulbOutlined />, title: '主题：浅色', label: '浅色' },
  dark: { icon: <MoonOutlined />, title: '主题：深色', label: '深色' },
};

/* ── 布局刻度（对齐 index.css 令牌） ── */
const MENU_ITEM_HEIGHT = 36; // 规范：菜单项高 36-40px
const POPUP_GAP = 8;         // 弹出子菜单与侧栏的间距

/* ── 折叠态弹出子菜单（portal 渲染到 body，避免被侧栏 overflow 裁剪） ── */
interface PopupState {
  key: string;
  top: number;
  left: number;
}

function CollapsedSubmenu({
  popup,
  activeKey,
  onKeep,
  onScheduleClose,
  onNavigate,
}: {
  popup: PopupState;
  activeKey: string;
  onKeep: () => void;
  onScheduleClose: () => void;
  onNavigate: (route: string) => void;
}) {
  const parent = menuItems.find((i): i is ParentMenuItem => isParent(i) && i.key === popup.key);
  if (!parent) return null;

  // 估算弹层高度，防止超出视口底部
  const popupHeight = parent.children.length * (MENU_ITEM_HEIGHT + 2) + 12;
  const top = Math.min(popup.top, Math.max(16, window.innerHeight - popupHeight - 16));

  return createPortal(
    <div
      onMouseEnter={onKeep}
      onMouseLeave={onScheduleClose}
      style={{
        position: 'fixed',
        top,
        left: popup.left,
        zIndex: 1000,
        minWidth: 168,
        padding: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        background: 'var(--bg-primary)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      {parent.children.map((child) => {
        const active = activeKey === child.key;
        return (
          <div
            key={child.key}
            onClick={() => onNavigate(child.route)}
            style={{
              height: MENU_ITEM_HEIGHT,
              display: 'flex',
              alignItems: 'center',
              padding: '0 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 13,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'background 0.2s ease, color 0.2s ease',
              color: active ? 'var(--accent-color)' : 'var(--text-secondary)',
              fontWeight: active ? 500 : 400,
              background: active ? 'var(--accent-alpha-08)' : 'transparent',
            }}
            onMouseEnter={(e) => {
              if (!active) e.currentTarget.style.background = 'var(--bg-tertiary)';
            }}
            onMouseLeave={(e) => {
              if (!active) e.currentTarget.style.background = 'transparent';
            }}
          >
            {child.label}
          </div>
        );
      })}
    </div>,
    document.body
  );
}

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
  // 主题三态：底部工具区循环切换；亮色补轻投影（暗色靠描边分层）
  const themePreference = useThemeStore((s) => s.preference);
  const cycleTheme = useThemeStore((s) => s.cycle);
  const themeResolved = useThemeStore((s) => s.resolved);

  // 任务选择器状态
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);

  // 折叠态弹出子菜单状态（锚定坐标 + 关闭延时器）
  const [popup, setPopup] = useState<PopupState | null>(null);
  const popupCloseTimer = useRef<number | null>(null);

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

  // 展开态不保留弹出子菜单
  useEffect(() => {
    if (!collapsed) setPopup(null);
  }, [collapsed]);

  // 卸载时清理关闭延时器
  useEffect(() => () => {
    if (popupCloseTimer.current !== null) window.clearTimeout(popupCloseTimer.current);
  }, []);

  const openPopup = (key: string, el: HTMLElement) => {
    if (popupCloseTimer.current !== null) {
      window.clearTimeout(popupCloseTimer.current);
      popupCloseTimer.current = null;
    }
    const rect = el.getBoundingClientRect();
    setPopup({ key, top: rect.top, left: rect.right + POPUP_GAP });
  };

  const schedulePopupClose = () => {
    if (popupCloseTimer.current !== null) window.clearTimeout(popupCloseTimer.current);
    popupCloseTimer.current = window.setTimeout(() => setPopup(null), 150);
  };

  const keepPopupOpen = () => {
    if (popupCloseTimer.current !== null) {
      window.clearTimeout(popupCloseTimer.current);
      popupCloseTimer.current = null;
    }
  };

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

  // 菜单项 hover 配色（激活项不参与 hover 变底）
  const menuItemHoverIn = (active: boolean) => (e: React.MouseEvent<HTMLDivElement>) => {
    if (!active) e.currentTarget.style.background = 'var(--bg-tertiary)';
  };
  const menuItemHoverOut = (active: boolean) => (e: React.MouseEvent<HTMLDivElement>) => {
    if (!active) e.currentTarget.style.background = 'transparent';
  };

  return (
    <div
      style={{
        width: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
        background: 'var(--bg-primary)',
        borderRight: '1px solid var(--border-color)',
        boxShadow: themeResolved === 'light' ? 'var(--shadow-sm)' : 'none',
        color: 'var(--text-primary)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease, background-color 0.2s ease, border-color 0.2s ease',
        zIndex: 20,
        overflow: 'hidden',
        flexShrink: 0,
        height: '100%',
      }}
    >
      {/* Logo 区 */}
      <div style={{
        padding: collapsed ? '16px 0' : '16px 16px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
      }}>
        {!collapsed && (
          <div style={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap', color: 'var(--accent-color)' }}>
            <CustomerServiceOutlined style={{ marginRight: 8 }} />
            安鉴·天穹
          </div>
        )}
        <button
          onClick={toggleSidebar}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 16,
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
        padding: collapsed ? '12px 8px' : '12px 10px',
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
                    else {
                      setPopup(null);
                      navigate(item.children[0]?.route || '/');
                    }
                  }}
                  onMouseEnter={(e) => {
                    if (collapsed) openPopup(item.key, e.currentTarget);
                    menuItemHoverIn(isParentActive)(e);
                  }}
                  onMouseLeave={(e) => {
                    if (collapsed) schedulePopupClose();
                    menuItemHoverOut(isParentActive)(e);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    height: MENU_ITEM_HEIGHT,
                    padding: '0 10px',
                    marginBottom: 4,
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    transition: 'background 0.2s ease, color 0.2s ease',
                    fontSize: 13,
                    color: isParentActive ? 'var(--accent-color)' : 'var(--text-secondary)',
                    fontWeight: isParentActive ? 500 : 400,
                    whiteSpace: 'nowrap',
                    background: isParentActive ? 'var(--accent-alpha-08)' : 'transparent',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                >
                  <span style={{ width: 24, fontSize: 16, textAlign: 'center', flexShrink: 0, display: 'inline-flex', justifyContent: 'center' }}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <>
                      <span style={{ flex: 1 }}>{item.label}</span>
                      <RightOutlined
                        style={{
                          fontSize: 10,
                          color: 'var(--text-muted)',
                          transition: 'transform 0.2s ease',
                          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                        }}
                      />
                    </>
                  )}
                </div>
                {/* 二级菜单 */}
                {!collapsed && isExpanded && (
                  <div style={{
                    marginLeft: 34,
                    paddingLeft: 8,
                    borderLeft: '1px solid var(--border-color)',
                    marginBottom: 8,
                  }}>
                    {item.children.map((child) => {
                      const active = activeKey === child.key;
                      return (
                        <div
                          key={child.key}
                          onClick={() => navigate(child.route)}
                          onMouseEnter={menuItemHoverIn(active)}
                          onMouseLeave={menuItemHoverOut(active)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            height: MENU_ITEM_HEIGHT,
                            padding: '0 10px',
                            margin: '2px 0',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            fontSize: 13,
                            color: active ? 'var(--accent-color)' : 'var(--text-secondary)',
                            fontWeight: active ? 500 : 400,
                            whiteSpace: 'nowrap',
                            background: active ? 'var(--accent-alpha-08)' : 'transparent',
                            transition: 'background 0.2s ease, color 0.2s ease',
                          }}
                        >
                          {child.label}
                        </div>
                      );
                    })}
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
              onMouseEnter={menuItemHoverIn(isActive)}
              onMouseLeave={menuItemHoverOut(isActive)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                height: MENU_ITEM_HEIGHT,
                padding: '0 10px',
                marginBottom: 4,
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                transition: 'background 0.2s ease, color 0.2s ease',
                fontSize: 13,
                color: isActive ? 'var(--accent-color)' : 'var(--text-secondary)',
                fontWeight: isActive ? 500 : 400,
                whiteSpace: 'nowrap',
                background: isActive ? 'var(--accent-alpha-08)' : 'transparent',
                justifyContent: collapsed ? 'center' : 'flex-start',
              }}
            >
              <span style={{ width: 24, fontSize: 16, textAlign: 'center', flexShrink: 0, display: 'inline-flex', justifyContent: 'center' }}>
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
            </div>
          );
        })}
      </div>

      {/* Footer 区 */}
      <div style={{
        padding: collapsed ? '12px 8px' : '12px 10px',
        borderTop: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}>
        {/* 任务选择器（仅展开时显示） */}
        {!collapsed && (
          <div style={{ padding: '4px 10px 10px' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 6 }}>当前任务</div>
            <Select
              value={currentTask?.task_id}
              style={{ width: '100%' }}
              placeholder="选择任务"
              size="small"
              options={taskOptions}
              loading={loading}
              notFoundContent={loading ? <Spin size="small" /> : '暂无任务'}
              onChange={handleTaskChange}
            />
            {currentTask && (
              <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Badge
                  status={currentTask.status === 'running' ? 'processing' : 'default'}
                  text={(
                    <span style={{
                      fontSize: 11,
                      color: currentTask.status === 'running' ? 'var(--success)' : 'var(--text-muted)',
                    }}>
                      {statusLabel(currentTask.status)}
                    </span>
                  )}
                />
              </div>
            )}
          </div>
        )}

        {/* 主题三态循环切换（system → light → dark） */}
        <div
          onClick={cycleTheme}
          title={THEME_META[themePreference].title}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: MENU_ITEM_HEIGHT,
            padding: '0 10px',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: 13,
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: 'background 0.2s ease, color 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          {THEME_META[themePreference].icon}
          {!collapsed && <span>{THEME_META[themePreference].label}</span>}
        </div>

        {/* Footer 菜单项 */}
        <div
          onClick={() => navigate('/settings')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: MENU_ITEM_HEIGHT,
            padding: '0 10px',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: 13,
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: 'background 0.2s ease, color 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <SettingOutlined style={{ fontSize: 15 }} />
          {!collapsed && <span>系统设置</span>}
        </div>
        <div
          onClick={handleLogout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: MENU_ITEM_HEIGHT,
            padding: '0 10px',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: 13,
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: 'background 0.2s ease, color 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <LogoutOutlined style={{ fontSize: 15 }} />
          {!collapsed && <span>用户退出</span>}
        </div>
        <div
          onClick={() => navigate('/status')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: MENU_ITEM_HEIGHT,
            padding: '0 10px',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: 13,
            justifyContent: collapsed ? 'center' : 'flex-start',
            transition: 'background 0.2s ease, color 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
        >
          <CustomerServiceOutlined style={{ fontSize: 15 }} />
          {!collapsed && <span>系统状态</span>}
        </div>
      </div>

      {/* 折叠态弹出子菜单（portal，避免被侧栏 overflow 裁剪） */}
      {popup && collapsed && (
        <CollapsedSubmenu
          popup={popup}
          activeKey={activeKey}
          onKeep={keepPopupOpen}
          onScheduleClose={schedulePopupClose}
          onNavigate={(route) => {
            setPopup(null);
            navigate(route);
          }}
        />
      )}
    </div>
  );
};

export default Sidebar;
