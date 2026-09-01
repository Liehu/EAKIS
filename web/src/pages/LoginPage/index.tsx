import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Button, message, Typography, Alert, Space } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, SafetyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { useThemeStore } from '@/store/themeStore';
import { login, getMe, getSystemStatus, initAdmin } from '@/api/auth';

const { Title, Text } = Typography;

type Mode = 'loading' | 'login' | 'setup';

/* ── 品牌渐变字（规范 --brand-ai 135deg：--brand-ai-start → --brand-ai-end） ── */
const brandGradientText: React.CSSProperties = {
  backgroundImage: 'linear-gradient(135deg, var(--brand-ai-start), var(--brand-ai-end))',
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  color: 'transparent',
  WebkitTextFillColor: 'transparent',
};

const LoginPage: React.FC = () => {
  const [mode, setMode] = useState<Mode>('loading');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  // 暗色氛围光按解析主题条件渲染（inline style 无法用 [data-theme] 选择器）
  const isDark = useThemeStore((s) => s.resolved) === 'dark';

  // 已登录则跳转
  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  // 检查系统初始化状态
  useEffect(() => {
    getSystemStatus()
      .then((res) => {
        setMode(res.initialized ? 'login' : 'setup');
      })
      .catch(() => {
        // 后端不可达时仍显示登录页
        setMode('login');
      });
  }, []);

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await login(values);

      let user;
      try {
        user = await getMe();
      } catch {
        user = {
          id: '',
          org_id: '',
          email: values.username,
          display_name: values.username,
          phone: null,
          avatar_url: null,
          is_active: true,
          last_login_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          role: 'analyst',
          permissions: [],
          teams: {},
        };
      }

      authLogin(res.access_token, res.refresh_token, user);
      message.success('登录成功');
      navigate('/');
    } catch {
      message.error('登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  const handleInitAdmin = async (values: { email: string; password: string; display_name: string }) => {
    setLoading(true);
    try {
      const res = await initAdmin(values);

      let user;
      try {
        user = await getMe();
      } catch {
        user = {
          id: '',
          org_id: '',
          email: values.email,
          display_name: values.display_name,
          phone: null,
          avatar_url: null,
          is_active: true,
          last_login_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          role: 'super_admin',
          permissions: [],
          teams: {},
        };
      }

      authLogin(res.access_token, res.refresh_token, user);
      message.success('管理员账户创建成功');
      navigate('/');
    } catch {
      message.error('创建失败，请检查输入信息');
    } finally {
      setLoading(false);
    }
  };

  /* ── 页面背景：bg-secondary；暗色主题加规范式氛围光（左上主光 + 右下弱光） ── */
  const pageBackground: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'var(--bg-secondary)',
    ...(isDark
      ? {
          backgroundImage:
            'radial-gradient(circle at top left, var(--accent-alpha-12), transparent 28rem), radial-gradient(circle at bottom right, var(--accent-alpha-04), transparent 24rem)',
        }
      : {}),
  };

  /* ── 登录卡：eakis-panel 语义 + radius-lg + 32-40px 内边距；亮色 shadow-md，暗色描边分层 ── */
  const loginCardStyle: React.CSSProperties = {
    width: 420,
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: isDark ? undefined : 'var(--shadow-md)',
  };

  if (mode === 'loading') {
    return (
      <div style={pageBackground}>
        <Card
          style={{ ...loginCardStyle, width: 380 }}
          styles={{ body: { padding: '40px 32px', textAlign: 'center' } }}
        >
          <Title level={3} style={{ ...brandGradientText, margin: 0, fontWeight: 700 }}>安鉴·天穹</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>正在检测系统状态...</Text>
        </Card>
      </div>
    );
  }

  return (
    <div style={pageBackground}>
      <Card style={loginCardStyle} styles={{ body: { padding: '40px 32px' } }}>
        {/* 品牌标识区 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={3} style={{ ...brandGradientText, margin: 0, fontWeight: 700 }}>安鉴·天穹</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>企业攻击面管理平台</Text>
        </div>

        {mode === 'setup' && (
          <Alert
            type="info"
            showIcon
            icon={<SafetyOutlined />}
            message="初始化系统"
            description="检测到系统尚未初始化，请创建第一个管理员账户。"
            style={{ marginBottom: 24 }}
          />
        )}

        <Form
          layout="vertical"
          onFinish={(values) => { void (mode === 'setup' ? handleInitAdmin(values as any) : handleLogin(values as any)); }}
        >
          {mode === 'setup' && (
            <Form.Item
              name="display_name"
              rules={[{ required: true, message: '请输入姓名' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-muted)' }} />}
                placeholder="管理员姓名"
                size="large"
              />
            </Form.Item>
          )}

          <Form.Item
            name={mode === 'setup' ? 'email' : 'username'}
            rules={[{ required: true, message: mode === 'setup' ? '请输入邮箱' : '请输入用户名' }]}
          >
            <Input
              prefix={<MailOutlined style={{ color: 'var(--text-muted)' }} />}
              placeholder={mode === 'setup' ? '管理员邮箱' : '用户名'}
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              mode === 'setup' ? { min: 8, message: '密码至少8位' } : {},
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: 'var(--text-muted)' }} />}
              placeholder={mode === 'setup' ? '设置管理员密码（至少8位）' : '密码'}
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">
              {mode === 'setup' ? '创建管理员账户' : '登 录'}
            </Button>
          </Form.Item>

          {mode === 'setup' && (
            <div style={{ textAlign: 'center' }}>
              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  已有账户？
                </Text>
                <Button type="link" size="small" onClick={() => setMode('login')}>
                  直接登录
                </Button>
              </Space>
            </div>
          )}
        </Form>
      </Card>
    </div>
  );
};

export default LoginPage;
