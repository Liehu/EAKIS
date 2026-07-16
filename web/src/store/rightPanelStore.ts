import { create } from 'zustand';

/**
 * 右侧上下文面板的共享状态。
 *
 * 各业务页（任务/知识库/模板/工具/报告）在行点击时调用 setItem 推入选中条目，
 * AppLayout 的 RightPanel 根据 kind 切换渲染。
 *
 * 企业/资产/漏洞页不使用本 store —— 它们仍用 graphStore 显示关系图谱。
 */

export type PanelKind =
  | 'graph' // 企业/资产/漏洞：关系图谱（由 graphStore 驱动，不走本 store）
  | 'task' // 任务详情
  | 'knowledge' // 知识库条目（漏洞/Payload/指纹/数据源/手册）
  | 'template' // 模板内容预览
  | 'tool' // 工具/执行详情
  | 'report'; // 报告文档预览

interface RightPanelState {
  kind: PanelKind;
  item: Record<string, unknown> | null;
  /** 子类型标识（如 knowledge 的 vuln/payload/fingerprint/datasource/handbook；
   *  template 的 task/report/prompt/attack；tool 的 info/execution） */
  subtype: string | null;
  setItem: (kind: PanelKind, item: Record<string, unknown> | null, subtype?: string | null) => void;
  clear: () => void;
}

export const useRightPanelStore = create<RightPanelState>((set) => ({
  kind: 'graph',
  item: null,
  subtype: null,
  setItem: (kind, item, subtype = null) => set({ kind, item, subtype }),
  clear: () => set({ kind: 'graph', item: null, subtype: null }),
}));
