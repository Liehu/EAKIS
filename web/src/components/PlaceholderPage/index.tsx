import React from 'react';
import { Result } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
    <Result
      icon={<ExperimentOutlined style={{ color: '#378ADD' }} />}
      title={title}
      subTitle={description || '该功能后端API尚未实现，当前为占位页面，后续将对接真实API。'}
      extra={null}
      style={{ padding: '40px 20px' }}
    />
  </div>
);

export default PlaceholderPage;
