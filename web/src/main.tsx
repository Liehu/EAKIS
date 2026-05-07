import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

async function bootstrap() {
  if (import.meta.env.VITE_API_MOCK === 'true') {
    const { worker } = await import('./api/mock/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

bootstrap();
