import './index.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { useAuthStore } from './store/authStore';
import { useThemeStore } from './store/themeStore';

async function bootstrap() {
  if (import.meta.env.VITE_API_MOCK === 'true') {
    const { worker } = await import('./api/mock/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }

  // Restore auth session from localStorage
  useAuthStore.getState().restoreSession();

  // 主题地基：render 前初始化主题（读偏好 → 写 html[data-theme] → system 态跟随系统），
  // 保证 React 首帧渲染时 antd token 与 CSS 变量均为已解析的正确主题
  useThemeStore.getState().init();

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

bootstrap();
