import React, { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import { useGraphStore } from '@/store/graphStore';
import { useThemeStore } from '@/store/themeStore';
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

/**
 * ECharts 画布（canvas）不解析 CSS 变量：按 useThemeStore.resolved 订阅主题，
 * 维护两套具体色板（规范 §03 锚点色）。系列色 5 档 / 关系线 accent 35% 透明。
 */
const CHART_PALETTES = {
  light: {
    canvasBg: '#ffffff',
    axisLine: '#e9ecef',
    axisLabel: '#6c757d',
    tooltipBg: '#ffffff',
    tooltipText: '#1a1a1a',
    tooltipBorder: '#e9ecef',
    series: ['#0066ff', '#7c3aed', '#20c997', '#ffc107', '#fd7e14'],
    edge: 'rgba(0, 102, 255, 0.35)',
    /** 中性普通节点（无分类语义）：亮色阶 */
    neutralFill: '#adb5bd',
    neutralBorder: '#ced4da',
    /** accent 节点描边同相亮一档（根节点/选中环） */
    accentRing: '#3385ff',
  },
  dark: {
    canvasBg: '#111827',
    axisLine: '#263244',
    axisLabel: '#a7b0c0',
    tooltipBg: '#1f2937',
    tooltipText: '#e5e7eb',
    tooltipBorder: '#263244',
    series: ['#60a5fa', '#a78bfa', '#2dd4bf', '#fbbf24', '#fb923c'],
    edge: 'rgba(96, 165, 250, 0.35)',
    /** 中性普通节点：暗色阶（保留原 #4a5568 系） */
    neutralFill: '#4a5568',
    neutralBorder: '#5a6577',
    accentRing: '#93c5fd',
  },
} as const;

/**
 * 节点分类色索引（取当前主题 series 色板，与资产页 TYPE_TOKENS 决策同源）：
 * - 资产占位图：总览/Web=accent(0) · 域名=brand-ai 紫系(1) · IP/小程序=低危青绿系(2) · APP=warning 黄系(3) · 证书=橙(4)
 * - 5 档系列色承载 6+ 语义分类，近似语义共用同档；无红档，漏洞取最接近高危语义的橙(4)
 * - 企业股权拓扑按层级区分：根主体=accent / 上级母公司=紫 / 普通子公司=中性（见 renderChart）
 */
const NODE_SERIES_INDEX: Record<string, number> = {
  asset_root: 0,
  web: 0,
  demo: 0,
  domain: 1,
  ip: 2,
  miniprogram: 2,
  app: 3,
  cert: 4,
  vuln: 4,
};

const GraphPanel: React.FC<GraphPanelProps> = ({ nodes = [], links = [] }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  // 主题解析结果：进 renderChart deps，主题切换时重绘
  const resolved = useThemeStore((s) => s.resolved);

  const graphType = useGraphStore((s) => s.graphType);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const graphHint = useGraphStore((s) => s.graphHint);
  // 业务页推入的拓扑数据（企业管理页推股权链等）
  const storeNodes = useGraphStore((s) => s.graphNodes);
  const storeLinks = useGraphStore((s) => s.graphLinks);

  const renderChart = useCallback(() => {
    if (!chartInstance.current) return;
    const palette = CHART_PALETTES[resolved];

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
      backgroundColor: palette.canvasBg,
      tooltip: {
        trigger: 'item',
        backgroundColor: palette.tooltipBg,
        borderColor: palette.tooltipBorder,
        textStyle: { color: palette.tooltipText },
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
          const baseSize = n > 20 ? 16 : 28;
          // 分类色：企业拓扑按层级（根=accent / 上级=紫 / 普通=中性）；占位图按节点 id 取系列色
          const seriesIdx = NODE_SERIES_INDEX[node.id];
          const fill = isRoot || isSelected
            ? palette.series[0]
            : isParent
              ? palette.series[1]
              : (!isEnterprise && seriesIdx != null ? palette.series[seriesIdx] : palette.neutralFill);
          return {
            id: node.id,
            name: node.name,
            symbolSize: isRoot ? 40 : (isParent ? 30 : baseSize),
            depth: node.depth,
            holding_ratio: node.holding_ratio ?? null,
            itemStyle: {
              color: fill,
              borderColor: isSelected ? palette.accentRing : (isRoot ? palette.accentRing : (isParent ? palette.series[1] : palette.neutralBorder)),
              borderWidth: isRoot ? 2 : (isSelected ? 2 : 0),
            },
            label: {
              show: true,
              position: 'bottom' as const,
              color: isRoot || isSelected || isParent ? palette.tooltipText : palette.axisLabel,
              fontWeight: isRoot ? 700 : (isParent ? 600 : 400),
              fontSize: isRoot ? 13 : (n > 20 ? 9 : 11),
            },
          };
        }),
        links: renderLinks.map((l: any) => ({
          source: l.source,
          target: l.target,
          holding_ratio: l.holding_ratio ?? null,
          lineStyle: { color: palette.edge, width: 1, curveness: 0.1 },
          label: isEnterprise && l.holding_ratio != null
            ? { show: n <= 25, formatter: `${l.holding_ratio}%`, color: palette.axisLabel, fontSize: 9 }
            : { show: !!l.label, formatter: l.label, color: palette.axisLabel, fontSize: 10 },
        })),
        lineStyle: { color: palette.edge, curveness: 0.1 },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3, color: palette.series[0] },
          label: { show: true },
        },
      }],
    };

    chartInstance.current.setOption(option, true);
  }, [nodes, links, storeNodes, storeLinks, graphType, selectedNodeId, resolved]);

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
    <div
      className="eakis-panel"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <div style={{
        padding: '16px 20px',
        fontWeight: 600,
        fontSize: 13,
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        color: 'var(--text-primary)',
        flexShrink: 0,
      }}>
        <span><ProjectOutlined style={{ marginRight: 8 }} />关系图谱</span>
        {graphHint && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{graphHint}</span>}
      </div>
      <div style={{ flex: 1, width: '100%', position: 'relative', background: CHART_PALETTES[resolved].canvasBg }}>
        {/* echarts 容器：React 不管理其子节点，避免 removeChild 冲突 */}
        <div ref={chartRef} style={{ position: 'absolute', inset: 0 }} />
        {/* 空状态提示：作为兄弟节点覆盖，不放进 echarts 容器内 */}
        {graphType === 'enterprise' && storeNodes.length === 0 && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', pointerEvents: 'none',
          }}>
            选择或采集企业后<br />在此显示股权控制链
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphPanel;
