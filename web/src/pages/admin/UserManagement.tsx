import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Switch, message, Space, Input as AntInput } from 'antd';
import { getUsers, createUser, updateUser, deleteUser } from '@/api/users';
import type { User, UserRole } from '@/types/user';

const roleLabels: Record<UserRole, string> = {
  super_admin: '超级管理员',
  org_admin: '组织管理员',
  team_lead: '团队负责人',
  engineer: '工程师',
  analyst: '分析师',
  auditor: '审计员',
};

// 徽章：语义令牌同色系底 + 同色字（规范 §06 徽章形态：r12 / 12px / 500）
const TokenBadge: React.FC<{ text: string; color: string; bg: string }> = ({ text, color, bg }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '4px 12px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 500,
      lineHeight: 1.2,
      whiteSpace: 'nowrap',
      color,
      background: bg,
    }}
  >
    {text}
  </span>
);

// 账号状态徽章：启用=success · 停用=muted（10% 同色底 + 同色字）
const AccountStatusBadge: React.FC<{ active: boolean }> = ({ active }) => (
  <TokenBadge
    text={active ? '启用' : '停用'}
    color={active ? 'var(--success)' : 'var(--text-muted)'}
    bg={
      active
        ? 'color-mix(in srgb, var(--success) 10%, transparent)'
        : 'color-mix(in srgb, var(--text-muted) 10%, transparent)'
    }
  />
);

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form] = Form.useForm();
  const [search, setSearch] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await getUsers({ page: 1, page_size: 100 });
      setUsers(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ role_name: 'engineer', is_active: true });
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setEditing(user);
    form.setFieldsValue({
      display_name: user.display_name,
      phone: user.phone,
      is_active: user.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await updateUser(editing.id, {
          display_name: values.display_name,
          phone: values.phone,
          is_active: values.is_active,
        });
        message.success('用户已更新');
      } else {
        await createUser(values);
        message.success('用户已创建');
      }
      setModalOpen(false);
      fetchUsers();
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (user: User) => {
    Modal.confirm({
      title: `停用用户 ${user.display_name}?`,
      content: '停用后用户将无法登录（软删除）。',
      okText: '停用',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteUser(user.id);
          message.success('用户已停用');
          fetchUsers();
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const filtered = users.filter(
    (u) => !search || u.email.includes(search) || u.display_name.includes(search),
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* 页头：左标题 + 右操作区（规范 §02） */}
      <div className="eakis-page-header">
        <span className="eakis-page-header-title">用户管理</span>
        <Space>
          <AntInput.Search placeholder="搜索邮箱/姓名" allowClear size="small" style={{ width: 200 }} onSearch={setSearch} />
          <Button type="primary" size="small" onClick={openCreate}>新建用户</Button>
        </Space>
      </div>
      <div className="eakis-page-content">
        <Table
          size="small"
          loading={loading}
          dataSource={filtered}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '姓名', dataIndex: 'display_name', key: 'display_name' },
            { title: '邮箱', dataIndex: 'email', key: 'email' },
            { title: '手机', dataIndex: 'phone', key: 'phone' },
            {
              title: '状态', dataIndex: 'is_active', key: 'is_active', width: 90,
              render: (v: boolean) => <AccountStatusBadge active={v} />,
            },
            {
              title: '最后登录', dataIndex: 'last_login_at', key: 'last_login', width: 180,
              render: (v: string | null) => (v ? new Date(v).toLocaleString('zh-CN') : '—'),
            },
            {
              title: '操作', key: 'action', width: 140,
              render: (_, record) => (
                <Space size={4}>
                  <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
                  <Button type="link" size="small" danger onClick={() => handleDelete(record)}>停用</Button>
                </Space>
              ),
            },
          ]}
        />
      </div>

      <Modal
        title={editing ? `编辑用户: ${editing.display_name}` : '新建用户'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <>
              <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                <Input placeholder="user@eakis.local" />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true, min: 8, message: '至少 8 位' }]}>
                <Input.Password placeholder="至少 8 位" />
              </Form.Item>
              <Form.Item name="role_name" label="角色" rules={[{ required: true }]}>
                <Select options={(Object.keys(roleLabels) as UserRole[]).map((r) => ({ value: r, label: roleLabels[r] }))} />
              </Form.Item>
            </>
          )}
          <Form.Item name="display_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="手机">
            <Input placeholder="选填" />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement;
