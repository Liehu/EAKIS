import { useEffect, useState } from 'react';
import { Table, Button, Modal, Form, Input, Select, Switch, Tag, message, Space, Input as AntInput } from 'antd';
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
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>用户管理</span>
        <Space>
          <AntInput.Search placeholder="搜索邮箱/姓名" allowClear size="small" style={{ width: 200 }} onSearch={setSearch} />
          <Button type="primary" size="small" onClick={openCreate}>新建用户</Button>
        </Space>
      </div>
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
            title: '状态', dataIndex: 'is_active', key: 'is_active', width: 80,
            render: (v: boolean) => (v ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
          },
          {
            title: '最后登录', dataIndex: 'last_login_at', key: 'last_login', width: 180,
            render: (v: string | null) => (v ? new Date(v).toLocaleString('zh-CN') : '—'),
          },
          {
            title: '操作', key: 'action', width: 140,
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => openEdit(record)}>编辑</Button>
                <Button size="small" danger onClick={() => handleDelete(record)}>停用</Button>
              </Space>
            ),
          },
        ]}
      />

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
