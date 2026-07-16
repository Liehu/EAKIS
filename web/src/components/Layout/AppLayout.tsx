import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import RightPanel from './RightPanel';
import ResizeHandle from '@/components/GraphPanel/ResizeHandle';
import { useGraphStore } from '@/store/graphStore';
import { useRightPanelStore, type PanelKind } from '@/store/rightPanelStore';

// 关系图谱页面（右侧显示 GraphPanel）
const GRAPH_ROUTES = ['/companies', '/assets', '/vulnerabilities'];

function routeToPanelKind(pathname: string): PanelKind | null {
  if (GRAPH_ROUTES.some((p) => pathname === p || pathname.startsWith(p + '/'))) return 'graph';
  if (pathname.startsWith('/tasks')) return 'task';
  if (pathname.startsWith('/knowledge')) return 'knowledge';
  if (pathname.startsWith('/templates')) return 'template';
  if (pathname.startsWith('/tools')) return 'tool';
  if (pathname.startsWith('/reports')) return 'report';
  return null; // dashboard/admin 等：不显示右侧栏
}

const AppLayout: React.FC = () => {
  const location = useLocation();
  const setGraphTypeByRoute = useGraphStore((s) => s.setGraphTypeByRoute);
  const clearGraphData = useGraphStore((s) => s.clearGraphData);
  const clearPanel = useRightPanelStore((s) => s.clear);
  const [rightWidth, setRightWidth] = useState(400);

  const panelKind = routeToPanelKind(location.pathname);
  const showRight = panelKind !== null;

  // 路由变化时更新图谱类型 + 清空面板状态
  useEffect(() => {
    setGraphTypeByRoute(location.pathname);
    clearGraphData();
    clearPanel();
  }, [location.pathname, setGraphTypeByRoute, clearGraphData, clearPanel]);

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100%',
      overflow: 'hidden',
      background: '#0d0d1a',
    }}>
      {/* 左侧菜单栏 */}
      <Sidebar />

      {/* 右侧主体区域 */}
      <div style={{
        flex: 1,
        display: 'flex',
        padding: '20px 20px 20px 12px',
        gap: showRight ? 20 : 0,
        overflow: 'hidden',
      }}>
        {/* 中间数据面板 */}
        <div style={{
          flex: 1,
          background: '#1a1a2e',
          boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transition: 'all 0.2s',
          minWidth: 0,
        }}>
          <Outlet />
        </div>

        {/* 右侧面板（关系图谱 or 详情预览） */}
        {showRight && (
          <>
            <ResizeHandle onResize={setRightWidth} />
            <div style={{
              width: rightWidth,
              minWidth: 280,
              maxWidth: 800,
              flexShrink: 0,
            }}>
              <RightPanel />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AppLayout;
