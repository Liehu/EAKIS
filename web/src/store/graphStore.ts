import { create } from 'zustand';

type GraphType = 'enterprise' | 'asset' | 'attack' | 'module';

export interface GraphNodeData {
  id: string;
  name: string;
  symbolSize?: number;
  category?: number;
  depth?: number;
  holding_ratio?: number | null;
}

export interface GraphLinkData {
  source: string;
  target: string;
  label?: string;
  value?: number;
}

interface GraphState {
  graphType: GraphType;
  selectedNodeId: string | null;
  graphHint: string;
  // 拓扑数据（由各业务页推入：企业管理页推企业股权链，资产页推资产分类等）
  graphNodes: GraphNodeData[];
  graphLinks: GraphLinkData[];
  // 节点点击导航回调（由业务页设置：点击节点 → 切换到对应企业/资产详情）
  onNodeNavigate: ((id: string) => void) | null;
  setGraphType: (type: GraphType) => void;
  setGraphTypeByRoute: (pathname: string) => void;
  selectNode: (id: string | null) => void;
  setGraphData: (nodes: GraphNodeData[], links: GraphLinkData[]) => void;
  clearGraphData: () => void;
  setNodeNavigate: (cb: ((id: string) => void) | null) => void;
}

const routeGraphMap: Record<string, { type: GraphType; hint: string }> = {
  '/companies': { type: 'enterprise', hint: '股权控制链' },
  '/assets': { type: 'asset', hint: '资产分类拓扑' },
  '/tasks': { type: 'module', hint: '任务关联' },
  '/knowledge': { type: 'module', hint: '知识关联' },
  '/templates': { type: 'module', hint: '模板关联' },
  '/vulnerabilities': { type: 'module', hint: '漏洞关联' },
  '/reports': { type: 'module', hint: '报告关联' },
};

export const useGraphStore = create<GraphState>((set) => ({
  graphType: 'enterprise',
  selectedNodeId: null,
  graphHint: '关系图谱',
  graphNodes: [],
  graphLinks: [],
  onNodeNavigate: null,
  setGraphType: (type) => set({ graphType: type, selectedNodeId: null }),
  setGraphTypeByRoute: (pathname) => {
    for (const [prefix, config] of Object.entries(routeGraphMap)) {
      if (pathname === prefix || pathname.startsWith(prefix + '/')) {
        set({ graphType: config.type, graphHint: config.hint, selectedNodeId: null });
        return;
      }
    }
    set({ graphType: 'module', graphHint: '关联关系', selectedNodeId: null });
  },
  selectNode: (id) => set({ selectedNodeId: id }),
  setGraphData: (nodes, links) => set({ graphNodes: nodes, graphLinks: links }),
  clearGraphData: () => set({ graphNodes: [], graphLinks: [] }),
  setNodeNavigate: (cb) => set({ onNodeNavigate: cb }),
}));
