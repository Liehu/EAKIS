import React, { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import { useGraphStore } from '@/store/graphStore';
import { ProjectOutlined } from '@ant-design/icons';

interface GraphNode {
  id: string;
  name: string;
  symbolSize?: number;
  category?: number;
  depth?: number;
  holding_ratio?: number | null;
}

interface GraphLink {
  source: string;
  target: string;
  label?: string;
  value?: number;
}

interface GraphPanelProps {
  nodes?: GraphNode[];
  links?: GraphLink[];
}

// 模块类型的默认数据
const moduleNodes = [{ id: 'demo', name: '当前功能模块', symbolSize: 30 }];
const moduleLinks: GraphLink[] = [];

// 资产类型的默认数据
const assetNodes = [
  { id: 'asset_root', name: '资产总览', symbolSize: 36 },
  { id: 'ip', name: 'IP', symbolSize: 24 },
  { id: 'domain', name: '域名', symbolSize: 24 },
  { id: 'cert', name: '证书', symbolSize: 24 },
  { id: 'app', name: '应用', symbolSize: 24 },
];
const assetLinks: GraphLink[] = [
  { source: 'asset_root', target: 'ip' },
  { source: 'asset_root', target: 'domain' },
  { source: 'asset_root', target: 'cert' },
  { source: 'asset_root', target: 'app' },
];

const GraphPanel: React.FC<GraphPanelProps> = ({ nodes = [], links = [] }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const graphType = useGraphStore((s) => s.graphType);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const graphHint = useGraphStore((s) => s.graphHint);
  // 业务页推入的拓扑数据（企业管理页推股权链等）
  const storeNodes = useGraphStore((s) => s.graphNodes);
  const storeLinks = useGraphStore((s) => s.graphLinks);

  const renderChart = useCallback(() => {
    if (!chartInstance.current) return;

    // 优先用 store 数据（业务页推入）；其次用 props；最后用类型默认数据
    let renderNodes = storeNodes.length ? storeNodes : nodes;
    let renderLinks = storeLinks.length ? storeLinks : links;
    let isEmpty = false;
    if (graphType === 'enterprise' && renderNodes.length === 0) {
      // 企业股权链无数据：留空（显示提示），不用占位数据
      isEmpty = true;
    } else if (graphType === 'asset' && renderNodes.length === 0) {
      renderNodes = assetNodes;
      renderLinks = assetLinks;
    } else if (graphType === 'module' && renderNodes.length === 0) {
      renderNodes = moduleNodes;
      renderLinks = moduleLinks;
    }

    if (isEmpty) {
      chartInstance.current.setOption({ series: [{ type: 'graph', data: [], links: [] }] }, true);
      return;
    }

    // 企业拓扑：根节点(depth 0)高亮加大，按持股比例标注边
    const isEnterprise = graphType === 'enterprise';
    // 力导向参数随节点数缩放：节点多时减小排斥力，避免散开到画布外
    const n = renderNodes.length;
    const repulsion = isEnterprise ? Math.max(60, 400 - n * 8) : 300;
    const edgeLength = isEnterprise ? (n > 20 ? [40, 80] : [80, 140]) : 120;
    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        backgroundColor: '#1a1a2e',
        borderColor: '#2a2a4e',
        textStyle: { color: '#e2e8f0' },
        formatter: (p: any) => {
          if (p.dataType === 'node') {
            const ratio = p.data.holding_ratio != null ? ` (持股 ${p.data.holding_ratio}%)` : '';
            return `${p.data.name}${ratio}`;
          }
          if (p.dataType === 'edge') {
            const ratio = p.data.holding_ratio != null ? ` · 持股 ${p.data.holding_ratio}%` : '';
            return `${p.data.source} → ${p.data.target}${ratio}`;
          }
          return p.name;
        },
      },
      series: [{
        type: 'graph',
        layout: 'force',
        force: {
          repulsion,
          edgeLength,
          gravity: 0.1,
          layoutAnimation: true,
        },
        roam: true,
        draggable: true,
        cursor: 'pointer',
        data: renderNodes.map((node) => {
          const isRoot = isEnterprise && node.depth === 0;
          const isParent = isEnterprise && (node.depth ?? 0) < 0; // 上级母公司
          const isSelected = node.id === selectedNodeId;
          // 根节点(当前主体)=蓝色加大；上级母公司=青色；子公司=灰色
          const baseSize = n > 20 ? 16 : 28;
          return {
            id: node.id,
            name: node.name,
            symbolSize: isRoot ? 40 : (isParent ? 30 : baseSize),
            depth: node.depth,
            holding_ratio: node.holding_ratio ?? null,
            itemStyle: {
              color: isSelected ? '#378ADD' : (isRoot ? '#378ADD' : (isParent ? '#6399AA' : '#4a5568')),
              borderColor: isSelected || isRoot ? '#5fa0e8' : (isParent ? '#7ab5c7' : '#5a6577'),
              borderWidth: isRoot ? 2 : 0,
            },
            label: {
              show: true,
              color: isRoot ? '#fff' : (isParent ? '#a0d4e0' : '#cbd5e1'),
              fontWeight: isRoot ? 700 : (isParent ? 600 : 400),
              fontSize: isRoot ? 13 : (n > 20 ? 9 : 11),
            },
          };
        }),
        links: renderLinks.map((l: any) => ({
          source: l.source,
          target: l.target,
          holding_ratio: l.holding_ratio ?? null,
          lineStyle: { color: '#4a5568', width: 1, curveness: 0.1 },
          label: isEnterprise && l.holding_ratio != null
            ? { show: n <= 25, formatter: `${l.holding_ratio}%`, color: '#888', fontSize: 9 }
            : { show: !!l.label, formatter: l.label, color: '#e2e8f0', fontSize: 10 },
        })),
        lineStyle: { color: '#4a5568', curveness: 0.1 },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3, color: '#378ADD' },
          label: { show: true },
        },
      }],
    };

    chartInstance.current.setOption(option, true);
  }, [nodes, links, storeNodes, storeLinks, graphType, selectedNodeId]);

  // 初始化 echarts 实例（仅一次）+ 卸载时销毁。合并到一个 effect 避免竞态。
  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;

    // 容器可能初始尺寸为 0（flex 布局时序），等有尺寸再初始化
    const doInit = () => {
      if (chartInstance.current) return; // 已初始化
      if (el.offsetWidth === 0 || el.offsetHeight === 0) {
        // 容器还没布局好，下一帧重试
        requestAnimationFrame(doInit);
        return;
      }
      chartInstance.current = echarts.init(el);
      renderChart();
    };
    doInit();

    // 用 ResizeObserver 监听容器尺寸变化（比 window resize 更可靠）
    const ro = new ResizeObserver(() => {
      if (chartInstance.current && el.offsetWidth > 0 && el.offsetHeight > 0) {
        chartInstance.current.resize();
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    renderChart();
    chartInstance.current?.resize();
  }, [renderChart]);

  const handleNodeClick = useCallback((params: any) => {
    if (params?.dataType === 'node' && params?.data?.id) {
      const id = params.data.id;
      const store = useGraphStore.getState();
      store.selectNode(id);
      // 触发业务页注册的导航回调（切换数据区到对应企业/资产）
      if (store.onNodeNavigate) {
        store.onNodeNavigate(id);
      }
    }
  }, []);

  useEffect(() => {
    const chart = chartInstance.current;
    if (!chart) return;
    const handler = handleNodeClick as (p: any) => void;
    chart.on('click', handler);
    return () => {
      chart.off('click', handler);
    };
  }, [handleNodeClick]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#1a1a2e',
      borderRadius: 28,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '16px 20px',
        fontWeight: 700,
        borderBottom: '1px solid #2a2a4e',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        color: '#e2e8f0',
        flexShrink: 0,
      }}>
        <span><ProjectOutlined style={{ marginRight: 8 }} />关系图谱</span>
        {graphHint && <span style={{ fontSize: 12, color: '#666' }}>{graphHint}</span>}
      </div>
      <div style={{ flex: 1, width: '100%', position: 'relative', background: '#141422' }}>
        {/* echarts 容器：React 不管理其子节点，避免 removeChild 冲突 */}
        <div ref={chartRef} style={{ position: 'absolute', inset: 0 }} />
        {/* 空状态提示：作为兄弟节点覆盖，不放进 echarts 容器内 */}
        {graphType === 'enterprise' && storeNodes.length === 0 && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            color: '#555', fontSize: 13, textAlign: 'center', pointerEvents: 'none',
          }}>
            选择或采集企业后<br />在此显示股权控制链
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphPanel;
