import { RouterProvider } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { router } from './router';

const App: React.FC = () => (
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#378ADD',
        borderRadius: 6,
        fontSize: 13,
        colorBgContainer: '#1a1a2e',
        colorBgElevated: '#1a1a2e',
        colorBorderSecondary: '#2a2a4e',
      },
      components: {
        Layout: {
          siderBg: '#141422',
          headerBg: '#141422',
          bodyBg: '#0d0d1a',
        },
        Menu: {
          darkItemBg: 'transparent',
          darkItemSelectedBg: '#378ADD22',
          darkItemHoverBg: '#ffffff0a',
        },
        Table: {
          headerBg: '#1a1a2e',
          rowHoverBg: '#ffffff0a',
        },
        Card: {
          colorBorderSecondary: '#2a2a4e',
        },
      },
    }}
  >
    <RouterProvider router={router} />
  </ConfigProvider>
);

export default App;
