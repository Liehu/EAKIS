import { createBrowserRouter } from 'react-router-dom';
import AppLayout from '@/components/Layout/AppLayout';
import LoginPage from '@/pages/LoginPage';
import Dashboard from '@/pages/Dashboard';
import Keywords from '@/pages/Keywords';
import Assets from '@/pages/Assets';
import Vulnerabilities from '@/pages/Vulnerabilities';
import Reports from '@/pages/Reports';
import Settings from '@/pages/Settings';
import TaskManagement from '@/pages/TaskManagement';
import Companies from '@/pages/Companies';
import AgentManagement from '@/pages/AgentManagement';
import StatusPage from '@/pages/StatusPage';
import ExportRecords from '@/pages/ExportRecords';
import Interfaces from '@/pages/Interfaces';
import UserManagement from '@/pages/admin/UserManagement';
import TeamManagement from '@/pages/admin/TeamManagement';
import AuditLogs from '@/pages/admin/AuditLogs';
import VulnKnowledgePage from '@/pages/Knowledge/VulnKnowledge';
import PayloadsPage from '@/pages/Knowledge/Payloads';
import FingerprintPage from '@/pages/Knowledge/Fingerprints';
import DatasourcePage from '@/pages/Knowledge/Datasources';
import HandbookPage from '@/pages/Knowledge/Handbooks';
import TemplateManagement from '@/pages/Templates/TemplateManagement';
import ToolManagement from '@/pages/Tools';
import PlaceholderPage from '@/components/PlaceholderPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      // 一级 flat 路由
      { index: true, element: <Dashboard /> },
      { path: 'companies', element: <Companies /> },
      { path: 'assets', element: <Assets /> },
      { path: 'vulnerabilities', element: <Vulnerabilities /> },
      { path: 'tools', element: <ToolManagement /> },
      { path: 'reports', element: <Reports /> },
      { path: 'settings', element: <Settings /> },
      { path: 'status', element: <StatusPage /> },
      { path: 'agent-management', element: <AgentManagement /> },
      { path: 'interfaces', element: <Interfaces /> },

      // 系统管理（RBAC）
      { path: 'admin/users', element: <UserManagement /> },
      { path: 'admin/teams', element: <TeamManagement /> },
      { path: 'admin/audit-logs', element: <AuditLogs /> },

      // 任务管理子路由
      { path: 'tasks', element: <TaskManagement /> },
      { path: 'tasks/scan', element: <PlaceholderPage title="扫描任务" description="支持多企业扫描任务编排与监控" /> },
      { path: 'tasks/import', element: <PlaceholderPage title="导入任务" description="批量导入资产、漏洞、情报数据" /> },
      { path: 'tasks/export', element: <ExportRecords /> },
      { path: 'tasks/drill', element: <PlaceholderPage title="演练任务" description="红蓝对抗演练任务管理与编排" /> },

      // 知识库管理子路由
      { path: 'knowledge/vulns', element: <VulnKnowledgePage /> },
      { path: 'knowledge/keywords', element: <Keywords /> },
      { path: 'knowledge/payloads', element: <PayloadsPage /> },
      { path: 'knowledge/fingerprints', element: <FingerprintPage /> },
      { path: 'knowledge/datasources', element: <DatasourcePage /> },
      { path: 'knowledge/handbooks', element: <HandbookPage /> },

      // 模板管理子路由
      { path: 'templates/task', element: <TemplateManagement /> },
      { path: 'templates/report', element: <TemplateManagement /> },
      { path: 'templates/prompt', element: <TemplateManagement /> },
      { path: 'templates/attack', element: <TemplateManagement /> },

      // 保留旧路由（兼容，后续可移除）
      { path: 'pentest', element: <PlaceholderPage title="自动渗透" description="功能已迁移至演练任务模块" /> },
    ],
  },
]);
