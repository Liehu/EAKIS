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
        Table: {
          headerBg: '#141422',
          rowHoverBg: '#ffffff0a',
          borderColor: '#2a2a4e',
        },
        Tabs: {
          inkBarColor: '#378ADD',
          itemActiveColor: '#378ADD',
          itemSelectedColor: '#378ADD',
          itemHoverColor: '#378ADD',
        },
        Modal: {
          contentBg: '#1a1a2e',
          headerBg: '#1a1a2e',
        },
      },
    }}
  >
    <RouterProvider router={router} />
  </ConfigProvider>
);

export default App;
