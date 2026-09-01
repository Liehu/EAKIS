import { useMemo } from 'react';
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import type { ThemeConfig } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useThemeStore } from './store/themeStore';
import { router } from './router';

/**
 * antd 主题令牌 —— 与 src/index.css 双主题 CSS 变量同源
 * （规范 §03.2 全局变量对照 / §03.3 暗色 Surface 阶）。
 * 亮色：白卡 + 轻投影分层；暗色：明度阶 + 1px 描边分层。
 */

const lightTokens: ThemeConfig['token'] = {
  colorPrimary: '#0066ff',
  colorInfo: '#0066ff',
  colorLink: '#0066ff',
  colorBgLayout: '#f8f9fa',
  colorBgContainer: '#ffffff',
  colorBgElevated: '#ffffff',
  colorText: '#1a1a1a',
  colorTextSecondary: '#6c757d',
  colorTextTertiary: '#adb5bd',
  colorBorder: '#e9ecef',
  colorBorderSecondary: '#e9ecef',
  colorSuccess: '#28a745',
  colorWarning: '#ffc107',
  colorError: '#dc3545',
  borderRadius: 6,
  fontSize: 13,
  // 与 index.css --font-sans 同值（规范 §04 唯一全局正文字族）
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
};

const darkTokens: ThemeConfig['token'] = {
  colorPrimary: '#60a5fa',
  colorInfo: '#60a5fa',
  colorLink: '#60a5fa',
  colorBgLayout: '#0b1120',
  colorBgContainer: '#111827',
  colorBgElevated: '#1f2937',
  colorText: '#e5e7eb',
  colorTextSecondary: '#a7b0c0',
  colorTextTertiary: '#6b7280',
  colorBorder: '#263244',
  colorBorderSecondary: '#263244',
  colorSuccess: '#34d399',
  colorWarning: '#fbbf24',
  colorError: '#f87171',
  borderRadius: 6,
  fontSize: 13,
  // 与亮色同族：字族是排版资产而非主题变量，避免主题切换时 antd 组件回退默认字体
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
};

/** 组件级 token：亮色 */
const lightComponents: ThemeConfig['components'] = {
  Table: {
    headerBg: '#f1f3f5',
    rowHoverBg: '#f8f9fa',
    borderColor: '#e9ecef',
    headerColor: '#6c757d',
  },
  Tabs: {
    inkBarColor: '#0066ff',
    itemActiveColor: '#0066ff',
    itemSelectedColor: '#0066ff',
    itemHoverColor: '#0066ff',
  },
  Modal: {
    contentBg: '#ffffff',
    headerBg: '#ffffff',
  },
  Button: {
    primaryShadow: 'none',
    defaultShadow: 'none',
    dangerShadow: 'none',
  },
};

/** 组件级 token：暗色（表头取 Surface 阶 #172033，行 hover 亮化 #2b374b，规范 §03.3） */
const darkComponents: ThemeConfig['components'] = {
  Table: {
    headerBg: '#172033',
    rowHoverBg: '#2b374b',
    borderColor: '#263244',
    headerColor: '#a7b0c0',
  },
  Tabs: {
    inkBarColor: '#60a5fa',
    itemActiveColor: '#60a5fa',
    itemSelectedColor: '#60a5fa',
    itemHoverColor: '#60a5fa',
  },
  Modal: {
    contentBg: '#111827',
    headerBg: '#111827',
  },
  Button: {
    primaryShadow: 'none',
    defaultShadow: 'none',
    dangerShadow: 'none',
  },
};

const App: React.FC = () => {
  // 订阅解析后的主题（system 已由 themeStore 用 matchMedia 实时解析）
  const resolved = useThemeStore((s) => s.resolved);

  const themeConfig = useMemo<ThemeConfig>(
    () => ({
      algorithm:
        resolved === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: resolved === 'dark' ? darkTokens : lightTokens,
      components: resolved === 'dark' ? darkComponents : lightComponents,
    }),
    [resolved],
  );

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <RouterProvider router={router} />
    </ConfigProvider>
  );
};

export default App;
