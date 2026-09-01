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
      background: 'var(--bg-secondary)',
    }}>
      {/* 左侧菜单栏 */}
      <Sidebar />

      {/* 右侧主体区域：外层 padding/gap 按 4px 刻度收敛（16px） */}
      <div style={{
        flex: 1,
        display: 'flex',
        padding: 16,
        gap: showRight ? 16 : 0,
        overflow: 'hidden',
        minWidth: 0,
      }}>
        {/* 中间数据面板：eakis-panel 语义（暗色 1px 描边分层 / 亮色轻投影），圆角 radius-md */}
        <div
          className="eakis-panel"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            transition: 'background-color 0.2s ease, border-color 0.2s ease',
            minWidth: 0,
          }}
        >
          <Outlet />
        </div>

        {/* 右侧面板（关系图谱 or 详情预览）：min 280 / max 800 */}
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
