import { useMemo } from 'react';
import type { DAGNode, DAGEdge } from '@/types/template';

// 轻量 DAG 可视化 (无第三方图库依赖, 用 SVG + 定位渲染节点和边)
// 节点按层级自动布局; 仅展示, 编辑通过 JSON 面板。

const NODE_W = 120;
const NODE_H = 44;
const COL_GAP = 60;
const ROW_GAP = 30;

interface Props {
  nodes: DAGNode[];
  edges: DAGEdge[];
}

const nodeTypeColor: Record<string, string> = {
  recon: '#3b82f6', vuln_scan: '#f59e0b', exploit: '#ef4444',
  lateral: '#8b5cf6', data_exfil: '#ec4899',
};

const DAGViewer: React.FC<Props> = ({ nodes, edges }) => {
  // 按 BFS 层级布局
  const { positioned, width, height } = useMemo(() => {
    if (nodes.length === 0) return { positioned: [] as Array<DAGNode & { x: number; y: number }>, width: 0, height: 0 };
    const inDeg: Record<string, number> = {};
    nodes.forEach((n) => (inDeg[n.id] = 0));
    edges.forEach((e) => { inDeg[e.target] = (inDeg[e.target] || 0) + 1; });

    const level: Record<string, number> = {};
    const queue = nodes.filter((n) => (inDeg[n.id] || 0) === 0).map((n) => n.id);
    queue.forEach((id) => (level[id] = 0));
    const adj: Record<string, string[]> = {};
    edges.forEach((e) => { (adj[e.source] ||= []).push(e.target); });
    let head = 0;
    while (head < queue.length) {
      const cur = queue[head++];
      (adj[cur] || []).forEach((nxt) => {
        level[nxt] = Math.max(level[nxt] || 0, level[cur] + 1);
        queue.push(nxt);
      });
    }
    nodes.forEach((n) => { if (level[n.id] === undefined) level[n.id] = 0; });

    // 按层级分组, 每层垂直排列
    const byLevel: Record<number, DAGNode[]> = {};
    nodes.forEach((n) => { (byLevel[level[n.id]] ||= []).push(n); });
    const maxLevel = Math.max(...Object.keys(byLevel).map(Number));
    const positioned = nodes.map((n) => {
      const lv = level[n.id];
      const siblings = byLevel[lv];
      const idx = siblings.indexOf(n);
      const x = lv * (NODE_W + COL_GAP) + 20;
      const y = idx * (NODE_H + ROW_GAP) + 20;
      return { ...n, x, y };
    });
    const maxRows = Math.max(...Object.values(byLevel).map((arr) => arr.length));
    return {
      positioned,
      width: (maxLevel + 1) * (NODE_W + COL_GAP) + 20,
      height: maxRows * (NODE_H + ROW_GAP) + 40,
    };
  }, [nodes, edges]);

  const nodeById = useMemo(() => {
    const m: Record<string, DAGNode & { x: number; y: number }> = {};
    positioned.forEach((n) => (m[n.id] = n));
    return m;
  }, [positioned]);

  if (nodes.length === 0) {
    return <div style={{ color: '#64748b', padding: 24, textAlign: 'center' }}>暂无节点</div>;
  }

  return (
    <div style={{ overflow: 'auto', border: '1px solid #1f2937', borderRadius: 8, background: '#0f172a' }}>
      <svg width={Math.max(width, 400)} height={height} style={{ display: 'block' }}>
        {/* edges */}
        {edges.map((e, i) => {
          const s = nodeById[e.source], t = nodeById[e.target];
          if (!s || !t) return null;
          const x1 = s.x + NODE_W, y1 = s.y + NODE_H / 2;
          const x2 = t.x, y2 = t.y + NODE_H / 2;
          const mx = (x1 + x2) / 2;
          return (
            <g key={i}>
              <path d={`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`} stroke="#475569" strokeWidth={1.5} fill="none" markerEnd="url(#arrow)" />
              <text x={mx} y={(y1 + y2) / 2 - 4} fill="#64748b" fontSize={9} textAnchor="middle">{e.action}</text>
            </g>
          );
        })}
        {/* nodes */}
        {positioned.map((n) => (
          <g key={n.id}>
            <rect x={n.x} y={n.y} width={NODE_W} height={NODE_H} rx={6}
              fill={nodeTypeColor[n.type] || '#334155'} opacity={0.85} stroke="#cbd5e1" strokeWidth={1} />
            <text x={n.x + NODE_W / 2} y={n.y + 18} fill="#fff" fontSize={11} fontWeight={600} textAnchor="middle">{n.label}</text>
            <text x={n.x + NODE_W / 2} y={n.y + 34} fill="#e2e8f0" fontSize={9} textAnchor="middle">{n.type}</text>
          </g>
        ))}
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#475569" />
          </marker>
        </defs>
      </svg>
    </div>
  );
};

export default DAGViewer;
