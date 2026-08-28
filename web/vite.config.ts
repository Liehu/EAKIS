import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // WSL 镜像网络下 3000 常被 Windows 侧占用；端口可由环境变量覆盖
    port: Number(process.env.VITE_DEV_PORT || 3000),
    // 沙箱/受限网络环境下 HMR 端口探测会全部误报占用，联调时可禁用（刷新页面即可）
    hmr: process.env.VITE_DISABLE_HMR === '1' ? false : undefined,
    proxy: {
      '/v1': {
        target: 'http://localhost:18000',
        changeOrigin: true,
      },
    },
  },
});
