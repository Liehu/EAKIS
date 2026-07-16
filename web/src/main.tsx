import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { useAuthStore } from './store/authStore';

async function bootstrap() {
  if (import.meta.env.VITE_API_MOCK === 'true') {
    const { worker } = await import('./api/mock/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }

  // Restore auth session from localStorage
  useAuthStore.getState().restoreSession();

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

bootstrap();
